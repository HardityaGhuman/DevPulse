from app.schemas import DigestResult, DigestContext, WaitingPR, ShippedPR, WorkItem
from app.services.email import _build_digest_html, _delivery_date

CTX = DigestContext(
    github_username="me", period_start="2026-07-01", period_end="2026-07-02",
    commits=12, prs_opened=2, prs_merged=3, issues_opened=1, reviews=5,
    repos_active=["me/aria", "dev/core"], streak_days=5,
    waiting_prs=[WaitingPR(repo="me/aria", number=7, title="Refactor navigation layout",
                           url="https://x/7", age_days=6, additions=120, deletions=5,
                           changed_files=14, mergeable="CONFLICTING",
                           reason="review_requested")],
    shipped_prs=[ShippedPR(repo="me/aria", number=21, title="Memory Persistence",
                           url="https://x/21")],
    work_log=[WorkItem(repo="me/aria", headline="Added memory adapter", commits=2)],
    deltas={"commits": 2, "prs_opened": -1, "prs_merged": 1, "issues_opened": 0, "reviews": 2},
)
RES = DigestResult(headline="Steady day on aria.", momentum="rising")


def test_html_contains_facts_and_sections():
    html = _build_digest_html(RES, CTX, "2026-07-01", "2026-07-02")
    assert "Steady day on" in html                   # LLM headline ("aria" gets an emphasis span)
    assert "Refactor navigation layout" in html     # waiting PR (mac card / needs attention)
    assert "me/aria" in html
    assert "CONFLICT" in html                        # CONFLICTING pill (mac card)
    assert "Merge conflict" in html                  # needs-attention status
    assert "Memory Persistence" in html              # shipped PR title
    assert "Shipped Today" in html                   # section label (CSS uppercases it)
    assert "Added memory adapter" in html            # work-log headline
    assert "2 commits" in html                       # grouped commit count
    assert "PRS MERGED" in html                      # stat label
    assert '<span style="color:#EA580C;">DAY STREAK</span>' in html   # full streak label is orange
    assert "RISING" not in html                       # momentum/RISING badge dropped (Stitch spec)
    assert ">REVIEW</span>" not in html               # mac card carries only the CONFLICT pill
    assert _delivery_date() in html                   # masthead dateline = today's delivery date
    assert "+120" in html
    assert "14 files" in html
    assert 'href="https://x/7"' in html                # PR mentions (card/attention) are links
    assert html.strip().startswith("<")


def test_html_is_fixed_light():
    # Standardized 2026-07-04: the digest is fixed light in every client; colors are inline
    # (several clients strip <style>, which would otherwise revert links to default blue).
    # Light base because Gmail's mobile app inverts an already-dark email to light anyway.
    html = _build_digest_html(RES, CTX, "2026-07-01", "2026-07-02")
    assert 'content="light"' in html                  # light-only color-scheme
    assert "prefers-color-scheme" not in html         # theme-flip removed
    assert "background-color:#FFFFFF" in html         # paper-white sheet
    assert "background-color:#F9F9F8" in html          # mac panel tint (card on white)
    assert "box-shadow:" in html                       # newspaper drop shadow on the frame
    assert "color:#1A1C1C;text-decoration:none" in html   # links carry inline color (no Gmail blue)


def test_html_empty_states():
    ctx = CTX.model_copy(update={"waiting_prs": [], "shipped_prs": [], "work_log": []})
    html = _build_digest_html(RES, ctx, "2026-07-01", "2026-07-02")
    assert "No code shipped today." in html
    assert "Nothing needs your attention" in html


def test_html_shipped_summary_line():
    # AI-summary fact lines are templated from counts, never invented by the LLM.
    merged = CTX.model_copy(update={"shipped_prs": [], "prs_merged": 0})
    assert "No code was merged today." in _build_digest_html(RES, merged, "a", "b")


def test_html_escapes_malicious_pr_title():
    ctx = CTX.model_copy(update={"waiting_prs": [WaitingPR(
        repo="me/x", number=1, title='<script>alert(1)</script>"onmouseover',
        url="javascript:alert(1)", age_days=1, reason="yours")]})
    html = _build_digest_html(RES, ctx, "2026-07-01", "2026-07-02")
    assert "<script>alert(1)</script>" not in html      # escaped
    assert "&lt;script&gt;" in html
    assert 'href="javascript:alert(1)"' not in html      # unsafe scheme dropped
    assert 'href="#"' in html
