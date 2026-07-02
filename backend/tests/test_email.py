from app.schemas import DigestResult, DigestContext, WaitingPR
from app.services.email import _build_digest_html

CTX = DigestContext(
    github_username="me", period_start="2026-07-01", period_end="2026-07-02",
    commits=12, prs_opened=2, prs_merged=3, issues_opened=1, reviews=5,
    repos_active=["me/aria", "dev/core"], streak_days=5,
    waiting_prs=[WaitingPR(repo="me/aria", number=7, title="Refactor navigation layout",
                           url="https://x/7", age_days=6, additions=120, deletions=5,
                           changed_files=14, mergeable="CONFLICTING",
                           reason="review_requested")],
    deltas={"commits": 2, "prs_opened": -1, "issues_opened": 0, "reviews": 2},
)
RES = DigestResult(headline="Steady day on aria.", momentum="rising")


def test_html_contains_facts_and_pills():
    html = _build_digest_html(RES, CTX, "2026-07-01", "2026-07-02")
    assert "Steady day on aria." in html
    assert "Refactor navigation layout" in html
    assert "me/aria" in html
    assert "Conflict" in html            # CONFLICTING -> Conflict pill
    assert "Review requested" in html
    assert "5-day streak" in html
    assert "RISING" in html              # momentum pill
    assert "+120" in html
    assert "14 files" in html
    assert html.strip().startswith("<")


def test_html_empty_waiting_state():
    ctx = CTX.model_copy(update={"waiting_prs": []})
    html = _build_digest_html(RES, ctx, "2026-07-01", "2026-07-02")
    assert "Nothing needs your review" in html


def test_html_escapes_malicious_pr_title():
    ctx = CTX.model_copy(update={"waiting_prs": [WaitingPR(
        repo="me/x", number=1, title='<script>alert(1)</script>"onmouseover',
        url="javascript:alert(1)", age_days=1, reason="yours")]})
    html = _build_digest_html(RES, ctx, "2026-07-01", "2026-07-02")
    assert "<script>alert(1)</script>" not in html      # escaped
    assert "&lt;script&gt;" in html
    assert 'href="javascript:alert(1)"' not in html      # unsafe scheme dropped
    assert 'href="#"' in html
