"""
DevPulse — Email Service (Resend only)

Renders the editorial digest (broadsheet masthead, serif numerals, mono labels) and sends it
via Resend. Facts come straight from DigestContext; the LLM contributes only the one-line
headline — every other line is rendered from GitHub data, never invented.

The layout is a hand-built, email-safe (tables + inline styles) port of the Stitch screen
"DevPulse Responsive Email Digest - Light/Dark Comparison" (project: DevPulse Editorial
Dashboard), standardized on the LIGHT variant: the digest is fixed light in every client,
regardless of system theme (decision 2026-07-04 — replaces the earlier fixed-dark approach).
Reason: Gmail's mobile app runs its own dark-mode color engine that strips our declarations
and inverts an already-dark email to light anyway; rather than fight it, we ship a light base
so our design and the app's remap agree. Every color is still INLINE: several clients (Gmail
apps especially) strip <style> blocks, which is also why links must carry their color inline
or they render the client's default blue.

The sheet is paper-white (#FFFFFF) framed by a darker border + drop shadow for a newspaper feel;
the mac-window preview card uses a subtle tint (#F9F9F8) so it still reads as a card on the
white sheet — an app screenshot with dark text.

Icons are monochrome text-glyphs on the meaning-carrying sections only: AI Summary (✦),
Work in Progress (<>), Needs Attention ([!]), card lightning (⚡︎). No webfont icons (clients
don't load them) and no color emoji — the attention marker is a bracketed bang, not ⚠, because
the warning triangle renders as a color emoji in many clients and breaks the monochrome look.

Section order mirrors the digest spec: 1 AI Summary · 2 Shipped · 3 Work in progress ·
4 Needs attention · 5 Today's work · 6 Last 7 days.
"""

import html
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import resend
from app.config import settings
from app.schemas import DigestResult, DigestContext

logger = logging.getLogger("devpulse.email")

# Delivery-time display. The digest can go out at any interval (6h/12h/daily/weekly), so the
# masthead + mac-card clock show the ACTUAL send time, not a fixed 8:00. Rendered in the
# recipient's own digest_timezone (falls back to IST, the default tool owner's tz).
_DEFAULT_TZ = ZoneInfo("Asia/Kolkata")


def _resolve_tz(timezone: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(timezone) if timezone else _DEFAULT_TZ
    except Exception:
        return _DEFAULT_TZ


def _delivery_time(tz: ZoneInfo = _DEFAULT_TZ) -> str:
    """Current wall-clock at render (= send time), e.g. '2:35 PM'."""
    return datetime.now(tz).strftime("%-I:%M %p")


def _delivery_date(tz: ZoneInfo = _DEFAULT_TZ) -> str:
    """Today's date at send, e.g. 'JUL 04, 2026' — the masthead dateline (a publication date,
    not the digest's period boundary, so it stays in step with _delivery_time)."""
    return datetime.now(tz).strftime("%b %d, %Y").upper()


def _esc(text: str) -> str:
    """HTML-escape any dynamic text (PR titles, repo names, LLM headline, commit headlines)."""
    return html.escape(str(text), quote=True)


def _safe_url(url: str) -> str:
    """Only allow http(s) links in hrefs; escape for attribute context."""
    u = str(url)
    return html.escape(u, quote=True) if u.startswith(("http://", "https://")) else "#"


# NOTE: single quotes only — these land inside style="…" attributes, a double quote
# would terminate the attribute early and silently drop every declaration after it.
_SERIF = "'Playfair Display', Georgia, 'Times New Roman', serif"
_SANS = "'Inter', -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
_MONO = "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
# Stat numerals: webfonts don't load in email, so fall back to Times (LINING figures) not
# Georgia (OLDSTYLE — 6/8 ride high, 3/4/7/9 drop below baseline → the stat row looked jagged).
_NUM = "'Playfair Display', 'Times New Roman', Times, serif"

# Fixed light palette (the standardized theme) — always inline, never class-only.
_BG = "#FFFFFF"          # sheet + body background (paper white)
_INK = "#1A1C1C"         # primary text (near-black)
_MUTED = "#71717A"       # secondary text (zinc-500 — legible on white)
_BRAND = "#5B5BD6"       # indigo accent (light-theme value, matches frontend)
_POS = "#16A34A"         # additions / up-deltas (green-600, readable on light)
_NEG = "#DC2626"         # deletions / down-deltas (red-600)
_STREAK = "#EA580C"      # streak orange (orange-600, darker for light bg)
_HAIR = "#EAEAEA"        # inner hairlines / rules
_EDGE = "#D4D4D8"        # sheet frame border (darker — the newspaper edge)
_CHIP_BG = "#F3F4F3"     # icon chips
_CARD_BG = "#F9F9F8"     # mac-window panel (subtle tint so it reads as a card on white)

# Monochrome text-glyphs (U+FE0E forces text, not emoji, presentation).
_ICON_AI = "&#10022;"                 # ✦ four-pointed star (auto_awesome)
_ICON_ATTN = "[!]"                     # bracketed bang — pairs with <>; NO emoji (⚠ renders as
                                      # a color emoji glyph in many clients, breaking the mono look)
_ICON_BOLT = "&#9889;&#65038;"        # ⚡︎ lightning, text-presentation
_ICON_CODE = "&lt;&gt;"               # <> (code)

# Window-relative copy per cadence. The digest window scales with frequency, so the daily-first
# wording ("Shipped Today", "Today's Work", "merged N today") would lie on a 6h or weekly send.
# Each section that describes the WINDOW pulls its label/verb from here. §6 is deliberately NOT
# here — it is always a fixed trailing 7 days ("Last 7 Days"), independent of cadence.
_WINDOW_COPY = {
    "6h":     {"brief": "6-HOURLY BRIEF",  "shipped": "Shipped (last 6h)",   "work": "Recent Work",       "when": "in the last 6 hours"},
    "12h":    {"brief": "12-HOURLY BRIEF", "shipped": "Shipped (last 12h)",  "work": "Recent Work",       "when": "in the last 12 hours"},
    "daily":  {"brief": "DAILY BRIEF",     "shipped": "Shipped Today",       "work": "Today's Work",      "when": "today"},
    "weekly": {"brief": "WEEKLY BRIEF",    "shipped": "Shipped This Week",   "work": "This Week's Work",  "when": "this week"},
}
_DEFAULT_COPY = _WINDOW_COPY["daily"]


def _copy_for(frequency: str | None) -> dict:
    return _WINDOW_COPY.get(frequency or "", _DEFAULT_COPY)


# Long lists become a wall of text on wide windows (a weekly §5 can be 60+ commits). Cap the
# shipped-PR and work-log lists and summarize the remainder as a single overflow line.
_MAX_SHIPPED = 6
_MAX_WORK = 6
# Merge commits are pure noise in the work log ("Merge pull request #N …") — drop them entirely.
_MERGE_PREFIXES = ("merge pull request", "merge branch", "merge remote-tracking")


def _overflow_line(text: str) -> str:
    return (f'<p style="font-family:{_MONO};font-size:11px;font-weight:500;color:{_MUTED};'
            f'letter-spacing:0.03em;margin:14px 0 0;">+ {text}</p>')


def _emphasize_headline(headline: str, context: DigestContext) -> str:
    """Port of the spec's lede emphasis: quoted spans → bold-italic-indigo; repo names →
    semibold-italic. Operates on ESCAPED text and never rewrites inside an emitted span."""
    esc = _esc(headline)
    quote_span = (rf'<span style="color:{_BRAND};font-weight:700;font-style:italic;">\g<0>'
                  r'</span>')
    esc = re.sub(r'&#8220;.{1,120}?&#8221;|“.{1,120}?”', quote_span, esc)
    esc = re.sub(r'&quot;.{1,120}?&quot;', quote_span, esc)

    names = {r.split("/")[-1] for r in context.repos_active}
    names |= {p.repo.split("/")[-1] for p in context.waiting_prs}
    names |= {p.repo.split("/")[-1] for p in context.shipped_prs}
    names = sorted((n for n in names if n), key=len, reverse=True)

    parts = re.split(r'(<span.*?</span>)', esc)      # only touch text outside spans
    for i, part in enumerate(parts):
        if part.startswith("<span"):
            continue
        for n in names:
            part = re.sub(rf'\b({re.escape(_esc(n))})\b',
                          r'<span style="font-weight:600;font-style:italic;">\1</span>',
                          part)
        parts[i] = part
    return "".join(parts)


def _label(num: str, text: str, icon: str = "") -> str:
    """Mono section label — identical size/weight for every section (1–6): 12px / 700."""
    lead = (f'<span style="font-size:16px;vertical-align:-1px;padding-right:8px;">{icon}</span>'
            if icon else '')
    return (f'<div style="font-family:{_MONO};font-size:12px;font-weight:700;color:{_BRAND};'
            f'letter-spacing:0.06em;text-transform:uppercase;margin:0 0 16px;">'
            f'{lead}{num}. {text}</div>')


def _rule() -> str:
    return (f'<div style="border-top:1px solid {_HAIR};'
            f'height:0;line-height:0;font-size:0;">&nbsp;</div>')


# ── Section 1 — AI summary + mac-window card ─────────────────────

def _summary_facts(context: DigestContext, copy: dict = _DEFAULT_COPY) -> str:
    """The two templated fact lines under the LLM headline — counts, never LLM prose."""
    m = context.prs_merged
    when = copy["when"]
    merged = (f"No code was merged {when}." if m == 0
              else f"You merged {m} pull request{'' if m == 1 else 's'} {when}.")
    k = len(context.waiting_prs)
    if k == 0:
        attn = "Nothing needs your attention right now."
    else:
        attn = (f"You have {k} item{'' if k == 1 else 's'} that "
                f"{'needs' if k == 1 else 'need'} your attention.")
    return (f'<p style="font-family:{_SANS};font-size:14px;line-height:1.5;color:{_MUTED};'
            f'margin:0 0 8px;">{merged}</p>'
            f'<p style="font-family:{_SANS};font-size:14px;line-height:1.5;color:{_MUTED};'
            f'margin:0;">{attn}</p>')


def _mac_card(context: DigestContext, tz: ZoneInfo = _DEFAULT_TZ) -> str:
    """Light 'inbox preview' panel — white card / dark text, an app screenshot on the sheet."""
    if context.waiting_prs:
        pr = context.waiting_prs[0]
        conflict = (f'<td align="right" valign="top" style="white-space:nowrap;padding-left:8px;">'
                    f'<span style="display:inline-block;padding:1px 4px;border-radius:2px;'
                    f'border:1px solid {_STREAK};font-family:{_MONO};font-size:7px;'
                    f'letter-spacing:0.05em;color:{_STREAK};">CONFLICT</span></td>'
                    if pr.mergeable == "CONFLICTING" else '<td></td>')
        body = (
            f'<div style="border-bottom:1px solid {_HAIR};padding:8px 0 12px;">'
            f'<table width="100%" role="presentation" cellpadding="0" cellspacing="0"><tr>'
            f'<td valign="top" style="font-family:{_MONO};font-size:10px;font-weight:500;'
            f'color:{_INK};">{_esc(pr.repo)} #{pr.number}</td>{conflict}</tr></table>'
            f'<p style="font-family:{_SANS};font-size:11px;font-weight:500;color:{_INK};'
            f'margin:4px 0;"><a href="{_safe_url(pr.url)}" style="color:{_INK};'
            f'text-decoration:none;font-weight:500;">{_esc(pr.title)}</a></p>'
            f'<div style="font-family:{_MONO};font-size:8px;">'
            f'<span style="color:{_POS};">+{pr.additions}</span>&nbsp;&nbsp;'
            f'<span style="color:{_NEG};">-{pr.deletions}</span>&nbsp;&nbsp;'
            f'<span style="color:{_MUTED};">{pr.changed_files} files</span></div>'
            f'</div>')
    else:
        body = (f'<p style="font-family:{_SANS};font-size:11px;color:{_MUTED};margin:4px 0;">'
                f"You're all caught up.</p>")

    return f"""
    <div style="background-color:{_CARD_BG};border:1px solid {_HAIR};border-radius:12px;overflow:hidden;">
      <div style="padding:8px 16px;border-bottom:1px solid {_HAIR};">
        <table width="100%" role="presentation" cellpadding="0" cellspacing="0"><tr>
          <td style="font-size:0;line-height:0;">
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:#FF5F56;"></span>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:#FFBD2E;margin-left:6px;"></span>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:#27C93F;margin-left:6px;"></span>
          </td>
          <td align="right" style="font-family:{_MONO};font-size:8px;letter-spacing:0.1em;color:{_MUTED};">INBOX &middot; {_delivery_time(tz)}</td>
        </tr></table>
      </div>
      <div style="padding:16px;">
        <div style="font-family:{_MONO};font-size:8px;color:{_MUTED};">DEVPULSE &middot; ISSUE 001</div>
        <div style="font-family:{_MONO};font-size:9px;color:{_MUTED};margin:16px 0 0;">{_ICON_BOLT}&nbsp;WAITING ON YOU</div>
        {body}
      </div>
    </div>"""


def _section_summary(digest: DigestResult, context: DigestContext,
                     tz: ZoneInfo = _DEFAULT_TZ, copy: dict = _DEFAULT_COPY) -> str:
    headline = _emphasize_headline(digest.headline, context)
    return f"""
    <table width="100%" role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td valign="top" width="56%" style="padding-right:24px;">
        {_label("1", "AI Summary", _ICON_AI).replace('margin:0 0 16px', 'margin:0 0 24px')}
        <p style="font-family:{_SANS};font-size:22px;line-height:1.25;font-weight:400;color:{_INK};margin:0 0 24px;">{headline}</p>
        {_summary_facts(context, copy)}
      </td>
      <td valign="top" width="44%">{_mac_card(context, tz)}</td>
    </tr></table>"""


# ── Section 2 — Shipped today ────────────────────────────────────

def _section_shipped(context: DigestContext, copy: dict = _DEFAULT_COPY) -> str:
    prs = context.shipped_prs
    if prs:
        rows = "".join(
            f'<p style="margin:0 0 10px;font-family:{_SANS};font-size:15px;">'
            f'<a href="{_safe_url(p.url)}" style="font-family:{_SERIF};color:{_INK};text-decoration:none;font-weight:700;">'
            f'PR #{p.number} &mdash; {_esc(p.title)}</a>'
            f'<span style="font-family:{_MONO};font-size:11px;color:{_MUTED};">&nbsp;&nbsp;{_esc(p.repo)}</span></p>'
            for p in prs[:_MAX_SHIPPED])
        extra = len(prs) - _MAX_SHIPPED
        if extra > 0:
            rows += _overflow_line(f"{extra} more merged")
        content = rows
    else:
        content = (f'<p style="font-family:{_SANS};font-size:14px;line-height:1.5;'
                   f'color:{_MUTED};margin:0;">No code shipped {copy["when"]}.</p>')
    return (f'{_label("2", copy["shipped"])}{_rule()}'
            f'<div style="padding-top:16px;">{content}</div>')


# ── Sections 3 + 4 — Work in progress · Needs attention ──────────

def _section_wip(context: DigestContext) -> str:
    authored = [p for p in context.waiting_prs if p.reason == "yours"]
    if authored:
        blocks = []
        for p in authored:
            opened = "Opened today" if p.age_days == 0 else f"Opened {p.age_days}d ago"
            blocks.append(
                f'<p style="font-family:{_MONO};font-size:10px;font-weight:500;color:{_MUTED};'
                f'letter-spacing:0.05em;margin:0 0 4px;">{_esc(p.repo)}</p>'
                f'<table width="100%" role="presentation" cellpadding="0" cellspacing="0"><tr>'
                f'<td valign="middle"><a href="{_safe_url(p.url)}" '
                f'style="font-family:{_SERIF};font-size:16px;font-weight:700;color:{_INK};text-decoration:none;">'
                f'PR #{p.number} &mdash; {_esc(p.title)}</a></td>'
                f'<td valign="middle" align="right" style="white-space:nowrap;padding-left:8px;">'
                f'<span style="display:inline-block;padding:2px 8px;border-radius:999px;'
                f'border:1px solid {_POS};color:{_POS};font-family:{_MONO};'
                f'font-size:9px;font-weight:500;letter-spacing:0.05em;">OPEN</span></td>'
                f'</tr></table>'
                f'<p style="font-family:{_SANS};font-size:12px;color:{_MUTED};margin:4px 0 0;">{opened}</p>'
                f'<div style="font-family:{_MONO};font-size:11px;font-weight:500;margin-top:8px;">'
                f'<span style="color:{_POS};">+{p.additions}</span>&nbsp;&nbsp;'
                f'<span style="color:{_NEG};">-{p.deletions}</span>&nbsp;&nbsp;'
                f'<span style="color:{_MUTED};">{p.changed_files} files</span></div>')
        content = '<div style="margin-bottom:16px;">' + \
                  '</div><div style="margin-bottom:16px;">'.join(blocks) + '</div>'
    else:
        content = (f'<p style="font-family:{_SANS};font-size:14px;color:{_MUTED};margin:0;">'
                   f'No open work in progress.</p>')
    return (f'{_label("3", "Work In Progress", _ICON_CODE)}{_rule()}'
            f'<div style="padding-top:16px;">{content}</div>')


def _attention_status(pr) -> str:
    if pr.mergeable == "CONFLICTING":
        return "Merge conflict"
    if pr.is_draft:
        return "Draft — not ready"
    if pr.reason == "review_requested":
        return "Review requested"
    return "Awaiting review"


def _section_attention(context: DigestContext) -> str:
    if context.waiting_prs:
        bullets = []
        for p in context.waiting_prs:
            kind = "PR" if not str(p.title).lower().startswith("issue") else "Issue"
            bullets.append(
                f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-bottom:24px;"><tr>'
                f'<td valign="top" style="padding-right:12px;padding-top:5px;">'
                f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
                f'background-color:{_BRAND};font-size:0;line-height:0;">&nbsp;</span></td>'
                f'<td valign="top">'
                f'<p style="font-family:{_SANS};font-size:14px;font-weight:700;color:{_INK};margin:0;line-height:1.4;">'
                f'<a href="{_safe_url(p.url)}" style="font-family:{_SERIF};color:{_INK};text-decoration:none;font-weight:700;">{kind} #{p.number} in {_esc(p.repo)}</a></p>'
                f'<p style="font-family:{_SANS};font-size:12px;color:{_MUTED};margin:0;line-height:1.5;">{_attention_status(p)}</p>'
                f'</td></tr></table>')
        content = "".join(bullets)
    else:
        content = (f'<p style="font-family:{_SANS};font-size:14px;color:{_MUTED};margin:0;">'
                   f"You're all clear.</p>")
    return (f'{_label("4", "Needs Attention", _ICON_ATTN)}{_rule()}'
            f'<div style="padding-top:16px;">{content}</div>')


def _section_wip_attention(context: DigestContext) -> str:
    return f"""
    <table width="100%" role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td valign="top" width="50%" style="padding-right:28px;">{_section_wip(context)}</td>
      <td valign="top" width="50%" style="border-left:1px solid {_HAIR};padding-left:28px;">{_section_attention(context)}</td>
    </tr></table>"""


# ── Section 5 — Today's work (commit-headline log) ───────────────

def _log_glyph(headline: str) -> str:
    """Mono glyph for the chip, derived from what the row describes."""
    h = str(headline).lower()
    if h.startswith("opened pr"):
        return "#"
    if h.startswith(("refactor", "rework", "rewrote")):
        return "~"
    return "+"


def _is_merge_commit(headline: str) -> bool:
    return str(headline).lower().startswith(_MERGE_PREFIXES)


def _section_work_log(context: DigestContext, copy: dict = _DEFAULT_COPY) -> str:
    # Drop merge-commit noise, then cap — a weekly window can carry 60+ commits, and an
    # uncapped list turns the digest into a wall of text.
    log = [w for w in context.work_log if not _is_merge_commit(w.headline)]
    if log:
        rows = "".join(
            f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-bottom:24px;"><tr>'
            f'<td valign="middle" style="padding-right:24px;">'
            f'<div style="width:32px;height:32px;background-color:{_CHIP_BG};'
            f'border:1px solid {_HAIR};border-radius:4px;text-align:center;line-height:32px;'
            f'font-family:{_MONO};font-size:13px;color:{_MUTED};">{_log_glyph(w.headline)}</div></td>'
            f'<td valign="middle">'
            f'<p style="font-family:{_SERIF};font-size:16px;font-weight:700;color:{_INK};margin:0;line-height:1.4;">{_esc(w.headline)}</p>'
            f'<p style="font-family:{_SANS};font-size:11px;color:{_MUTED};margin:1px 0 0;">'
            f'{_esc(w.repo)} &middot; {w.commits} commit{"" if w.commits == 1 else "s"}</p>'
            f'</td></tr></table>'
            for w in log[:_MAX_WORK])
        rest = log[_MAX_WORK:]
        if rest:
            more_commits = sum(w.commits for w in rest)
            more_repos = len({w.repo for w in rest})
            rows += _overflow_line(
                f'{more_commits} more commit{"" if more_commits == 1 else "s"} across '
                f'{more_repos} repo{"" if more_repos == 1 else "s"}')
        content = rows
    else:
        content = (f'<p style="font-family:{_SANS};font-size:14px;color:{_MUTED};margin:0;">'
                   f'No commits recorded {copy["when"]}.</p>')
    return f'{_label("5", copy["work"])}{_rule()}<div style="padding-top:24px;">{content}</div>'


# ── Section 6 — Last 7 days (stat strip) ─────────────────────────

def _stat(label: str, value, value_color: str = _INK) -> str:
    # Bare numeral + label. No period-over-period deltas — the header line carries momentum.
    return (f'<td align="center" valign="top" width="16.66%" style="padding:0 4px;">'
            f'<div style="font-family:{_NUM};font-size:28px;font-weight:700;color:{value_color};line-height:1.2;margin-bottom:4px;">{value}</div>'
            f'<div style="font-family:{_MONO};font-size:8px;font-weight:500;color:{_MUTED};letter-spacing:0.05em;">{label}</div>'
            f'</td>')


# One plain-language phrase per momentum verdict — the only "trend" signal in the digest.
_MOMENTUM_PHRASE = {
    "rising": "Momentum is building this week.",
    "steady": "Holding a steady pace this week.",
    "declining": "A quieter week than usual.",
}


def _section_stats(context: DigestContext, momentum: str) -> str:
    # Fixed trailing-7-day counts (context.week_stats) — NOT the digest window — so this strip
    # is honestly "Last 7 Days" at every cadence. Falls back to window counts for any older
    # cached context that predates week_stats. Streak stays streak_days (its own 365-day run).
    w = context.week_stats or {}
    prs_opened = w.get("prs_opened", context.prs_opened)
    prs_merged = w.get("prs_merged", context.prs_merged)
    reviews = w.get("reviews", context.reviews)
    issues_opened = w.get("issues_opened", context.issues_opened)
    repos_active = w.get("repos_active", len(context.repos_active))
    # Streak is the accent column: orange numeral + full orange label.
    streak_label = f'<span style="color:{_STREAK};">DAY STREAK</span>'
    phrase = _MOMENTUM_PHRASE.get(momentum, _MOMENTUM_PHRASE["steady"])
    caption = (f'<p style="font-family:{_SANS};font-size:13px;font-style:italic;color:{_MUTED};'
               f'margin:8px 0 0;">{phrase}</p>')
    strip = (
        f'<table width="100%" role="presentation" cellpadding="0" cellspacing="0" style="table-layout:fixed;"><tr>'
        f'{_stat("PRS OPENED", prs_opened)}'
        f'{_stat("PRS MERGED", prs_merged)}'
        f'{_stat("REVIEWS GIVEN", reviews)}'
        f'{_stat("ISSUES OPENED", issues_opened)}'
        f'{_stat("REPOS ACTIVE", repos_active)}'
        f'{_stat(streak_label, context.streak_days, value_color=_STREAK)}'
        f'</tr></table>')
    return f'{_label("6", "Last 7 Days")}{caption}{_rule()}<div style="padding-top:32px;">{strip}</div>'


# ── Footer ───────────────────────────────────────────────────────

def _footer() -> str:
    dash = _safe_url(f"{settings.frontend_url}/dashboard")
    return f"""
    {_rule()}
    <table width="100%" role="presentation" cellpadding="0" cellspacing="0" style="margin-top:32px;"><tr>
      <td valign="top" width="55%">
        <p style="font-family:{_SERIF};font-size:15px;font-weight:700;font-style:italic;color:{_BRAND};margin:0;">Private by design.</p>
        <p style="font-family:{_SANS};font-size:11px;line-height:1.5;color:{_MUTED};margin:4px 0 0;max-width:220px;">We read GitHub that you approve. Your code never leaves your repos.</p>
      </td>
      <td valign="top" align="right" width="45%">
        <p style="font-family:{_SANS};font-size:12px;font-weight:500;color:{_INK};margin:0 0 4px;">Manage frequency and repositories &rarr;</p>
        <a href="{dash}" style="font-family:{_SANS};font-size:12px;font-weight:500;color:{_BRAND};text-decoration:none;">Open DevPulse Dashboard</a>
      </td>
    </tr></table>
    <p style="font-family:{_MONO};font-size:9px;font-weight:500;color:{_MUTED};letter-spacing:0.1em;text-transform:uppercase;text-align:center;margin:32px 0 0;">
      You're receiving this because you subscribed to DevPulse. &middot; <a href="{dash}" style="color:{_MUTED};text-decoration:underline;">Unsubscribe</a> &middot; DevPulse &copy; 2026
    </p>"""


def _build_digest_html(digest: DigestResult, context: DigestContext,
                       period_start: str, period_end: str,
                       tz: ZoneInfo = _DEFAULT_TZ, frequency: str | None = None) -> str:
    copy = _copy_for(frequency)
    masthead = f"""
    <table width="100%" role="presentation" cellpadding="0" cellspacing="0">
      <tr>
        <td valign="bottom">
          <div style="font-family:{_SERIF};font-size:32px;font-weight:700;color:{_INK};letter-spacing:-0.02em;line-height:1;">DEVPULSE</div>
        </td>
        <td valign="bottom" align="right" style="white-space:nowrap;">
          <div style="font-family:{_MONO};font-size:12px;font-weight:500;color:{_INK};letter-spacing:0.1em;">ISSUE 001 &middot; {copy["brief"]}</div>
        </td>
      </tr>
      <tr>
        <td valign="top" style="padding-top:4px;">
          <div style="font-family:{_MONO};font-size:9px;font-weight:500;color:{_MUTED};letter-spacing:0.05em;white-space:nowrap;">A DEVELOPER'S BRIEF</div>
          <div style="font-family:{_MONO};font-size:9px;font-weight:500;color:{_MUTED};letter-spacing:0.05em;white-space:nowrap;margin-top:2px;">BUILT ON YOUR GITHUB</div>
        </td>
        <td valign="top" align="right" style="padding-top:4px;white-space:nowrap;">
          <div style="font-family:{_MONO};font-size:10px;font-weight:500;color:{_MUTED};letter-spacing:0.05em;">{_delivery_date(tz)} &middot; {_delivery_time(tz)}</div>
        </td>
      </tr>
    </table>"""

    gap = '<div style="height:48px;line-height:48px;font-size:0;">&nbsp;</div>'
    body = f"""
  <table width="640" role="presentation" cellpadding="0" cellspacing="0" align="center"
         bgcolor="{_BG}" style="max-width:640px;margin:0 auto;background-color:{_BG};">
    <tr><td style="padding:0;">
      <div style="border:1px solid {_EDGE};box-shadow:0 1px 2px rgba(0,0,0,0.06),0 14px 40px rgba(0,0,0,0.12);">
      <div style="padding:32px 32px 16px;">{masthead}</div>
      <div style="margin:0 32px;">{_rule()}</div>
      <div style="padding:40px 32px;">
      {_section_summary(digest, context, tz, copy)}{gap}
      {_section_shipped(context, copy)}{gap}
      {_section_wip_attention(context)}{gap}
      {_section_work_log(context, copy)}{gap}
      {_section_stats(context, digest.momentum)}
      </div>
      <div style="padding:0 32px 48px;">
      {_footer()}
      </div>
      </div>
    </td></tr>
  </table>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600;1,700&family=Playfair+Display:wght@700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{ color-scheme: light; supported-color-schemes: light; }}
  body {{ margin:0; padding:0; -webkit-text-size-adjust:100%; background:{_BG}; }}
</style>
</head>
<body bgcolor="{_BG}" style="margin:0;padding:40px 16px;background-color:{_BG};">
{body}
</body>
</html>"""


async def send_digest_email(to: str, subject: str, digest: DigestResult,
                            context: DigestContext, period_start: str, period_end: str,
                            timezone: str | None = None, frequency: str | None = None) -> bool:
    """Send a digest email via Resend. Returns True on success, False on failure.

    `timezone` is the recipient's IANA tz (their saved digest_timezone); the masthead/card
    delivery clock renders in it. Falls back to IST when unset/invalid. `frequency` selects the
    window-relative copy (labels/verbs) so the wording matches the digest's actual window.
    """
    tz = _resolve_tz(timezone)
    try:
        resend.api_key = settings.resend_api_key
        payload = {
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": _build_digest_html(digest, context, period_start, period_end, tz, frequency),
        }
        if settings.email_reply_to:
            payload["reply_to"] = settings.email_reply_to
        resend.Emails.send(payload)
        return True
    except Exception as e:
        logger.error("[email] failed to send digest to %s: %s", to, e)
        return False
