"""
DevPulse — Email Service (Resend only)

Renders the editorial digest (broadsheet masthead, serif numerals, mono labels) and sends it
via Resend. Facts come straight from DigestContext; the LLM contributes only the one-line
headline — every other line is rendered from GitHub data, never invented.

The layout is a hand-built, email-safe (tables + inline styles) port of the Stitch screen
"DevPulse Responsive Email Digest - Light/Dark Comparison" (project: DevPulse Editorial
Dashboard), standardized on the DARK variant: the digest is fixed dark in every client,
regardless of system theme (decision 2026-07-03 — replaces the earlier prefers-color-scheme
responsive approach). Every color is INLINE: several clients (Gmail apps especially) strip
<style> blocks, which is also why links must carry their color inline or they render the
client's default blue.

The mac-window preview card keeps its own darker panel (#121217) with white text — it's an
app screenshot inside the dark sheet.

Icons are monochrome Unicode text-glyphs (U+FE0E variation selector) on the meaning-carrying
sections only: AI Summary (✦), Work in Progress (<>), Needs Attention (⚠︎), card lightning.
No webfont icons (clients don't load them) and no color emoji.

Section order mirrors the digest spec: 1 AI Summary · 2 Shipped · 3 Work in progress ·
4 Needs attention · 5 Today's work · 6 Last 7 days.
"""

import html
import logging
import re
from datetime import datetime
import resend
from app.config import settings
from app.schemas import DigestResult, DigestContext

logger = logging.getLogger("devpulse.email")


def _esc(text: str) -> str:
    """HTML-escape any dynamic text (PR titles, repo names, LLM headline, commit headlines)."""
    return html.escape(str(text), quote=True)


def _safe_url(url: str) -> str:
    """Only allow http(s) links in hrefs; escape for attribute context."""
    u = str(url)
    return html.escape(u, quote=True) if u.startswith(("http://", "https://")) else "#"


def _fmt_date(value: str) -> str:
    """Broadsheet date: 'JUL 03, 2026'. Falls back to the raw string if it won't parse."""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(str(value), fmt).strftime("%b %d, %Y").upper()
        except (ValueError, TypeError):
            continue
    return _esc(value)


# NOTE: single quotes only — these land inside style="…" attributes, a double quote
# would terminate the attribute early and silently drop every declaration after it.
_SERIF = "'Playfair Display', Georgia, 'Times New Roman', serif"
_SANS = "'Inter', -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
_MONO = "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace"

# Fixed dark palette (the standardized theme) — always inline, never class-only.
_BG = "#0E0E12"          # sheet background
_INK = "#FFFFFF"         # primary text
_MUTED = "#A1A1AA"       # secondary text
_BRAND = "#8B8BF5"       # indigo accent (dark-theme value)
_POS = "#4ade80"         # additions / up-deltas
_NEG = "#f87171"         # deletions / down-deltas
_STREAK = "#FB923C"      # streak orange
_HAIR = "#2D2D35"        # hairlines / borders
_CHIP_BG = "#1A1A22"     # icon chips
_CARD_BG = "#121217"     # mac-window panel (darker than the sheet)

# Monochrome text-glyphs (U+FE0E forces text, not emoji, presentation).
_ICON_AI = "&#10022;"                 # ✦ four-pointed star (auto_awesome)
_ICON_ATTN = "&#9888;&#65038;"        # ⚠︎ warning triangle, text-presentation
_ICON_BOLT = "&#9889;&#65038;"        # ⚡︎ lightning, text-presentation
_ICON_CODE = "&lt;&gt;"               # <> (code)


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


def _delta(v: int) -> str:
    if v > 0:
        return f'<span style="font-family:{_MONO};font-size:9px;color:{_POS};">&#8593; {v}</span>'
    if v < 0:
        return (f'<span style="font-family:{_MONO};font-size:9px;color:{_NEG};">'
                f'&#8595; {abs(v)}</span>')
    return f'<span style="font-family:{_MONO};font-size:9px;color:{_MUTED};">&mdash;</span>'


# ── Section 1 — AI summary + mac-window card ─────────────────────

def _summary_facts(context: DigestContext) -> str:
    """The two templated fact lines under the LLM headline — counts, never LLM prose."""
    m = context.prs_merged
    merged = ("No code was merged today." if m == 0
              else f"You merged {m} pull request{'' if m == 1 else 's'} today.")
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


def _mac_card(context: DigestContext) -> str:
    """Dark 'inbox preview' panel — the standardized dark-base / white-text rendering."""
    if context.waiting_prs:
        pr = context.waiting_prs[0]
        conflict = (f'<td align="right" valign="top" style="white-space:nowrap;padding-left:8px;">'
                    f'<span style="display:inline-block;padding:1px 4px;border-radius:2px;'
                    f'border:1px solid rgba(249,115,22,0.5);font-family:{_MONO};font-size:7px;'
                    f'letter-spacing:0.05em;color:{_STREAK};">CONFLICT</span></td>'
                    if pr.mergeable == "CONFLICTING" else '<td></td>')
        body = (
            f'<div style="border-bottom:1px solid rgba(255,255,255,0.1);padding:8px 0 12px;">'
            f'<table width="100%" role="presentation" cellpadding="0" cellspacing="0"><tr>'
            f'<td valign="top" style="font-family:{_MONO};font-size:10px;font-weight:500;'
            f'color:{_INK};">{_esc(pr.repo)} #{pr.number}</td>{conflict}</tr></table>'
            f'<p style="font-family:{_SANS};font-size:11px;font-weight:500;color:{_INK};'
            f'margin:4px 0;">{_esc(pr.title)}</p>'
            f'<div style="font-family:{_MONO};font-size:8px;">'
            f'<span style="color:{_POS};">+{pr.additions}</span>&nbsp;&nbsp;'
            f'<span style="color:{_NEG};">-{pr.deletions}</span>&nbsp;&nbsp;'
            f'<span style="color:rgba(255,255,255,0.4);">{pr.changed_files} files</span></div>'
            f'</div>')
    else:
        body = (f'<p style="font-family:{_SANS};font-size:11px;color:{_MUTED};margin:4px 0;">'
                f'Inbox zero — nothing waiting.</p>')

    return f"""
    <div style="background-color:{_CARD_BG};border:1px solid rgba(255,255,255,0.1);border-radius:12px;overflow:hidden;">
      <div style="padding:8px 16px;border-bottom:1px solid rgba(255,255,255,0.1);">
        <table width="100%" role="presentation" cellpadding="0" cellspacing="0"><tr>
          <td style="font-size:0;line-height:0;">
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:#FF5F56;"></span>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:#FFBD2E;margin-left:6px;"></span>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background-color:#27C93F;margin-left:6px;"></span>
          </td>
          <td align="right" style="font-family:{_MONO};font-size:8px;letter-spacing:0.1em;color:rgba(255,255,255,0.4);">INBOX &middot; 8:00 AM</td>
        </tr></table>
      </div>
      <div style="padding:16px;">
        <div style="font-family:{_MONO};font-size:8px;color:rgba(255,255,255,0.4);">DEVPULSE &middot; ISSUE 001</div>
        <div style="font-family:{_MONO};font-size:9px;color:rgba(255,255,255,0.6);margin:16px 0 0;">{_ICON_BOLT}&nbsp;WAITING ON YOU</div>
        {body}
      </div>
    </div>"""


def _section_summary(digest: DigestResult, context: DigestContext) -> str:
    headline = _emphasize_headline(digest.headline, context)
    return f"""
    <table width="100%" role="presentation" cellpadding="0" cellspacing="0"><tr>
      <td valign="top" width="56%" style="padding-right:24px;">
        {_label("1", "AI Summary", _ICON_AI).replace('margin:0 0 16px', 'margin:0 0 24px')}
        <p style="font-family:{_SANS};font-size:22px;line-height:1.25;font-weight:400;color:{_INK};margin:0 0 24px;">{headline}</p>
        {_summary_facts(context)}
      </td>
      <td valign="top" width="44%">{_mac_card(context)}</td>
    </tr></table>"""


# ── Section 2 — Shipped today ────────────────────────────────────

def _section_shipped(context: DigestContext) -> str:
    if context.shipped_prs:
        rows = "".join(
            f'<p style="margin:0 0 10px;font-family:{_SANS};font-size:15px;">'
            f'<a href="{_safe_url(p.url)}" style="color:{_INK};text-decoration:none;font-weight:700;">'
            f'PR #{p.number} &mdash; {_esc(p.title)}</a>'
            f'<span style="font-family:{_MONO};font-size:11px;color:{_MUTED};">&nbsp;&nbsp;{_esc(p.repo)}</span></p>'
            for p in context.shipped_prs)
        content = rows
    else:
        content = (f'<p style="font-family:{_SANS};font-size:14px;line-height:1.5;'
                   f'color:{_MUTED};margin:0;">No code shipped today.</p>')
    return (f'{_label("2", "Shipped Today")}{_rule()}'
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
                f'style="font-family:{_SANS};font-size:15px;font-weight:700;color:{_INK};text-decoration:none;">'
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
                f'<p style="font-family:{_SANS};font-size:14px;font-weight:700;color:{_INK};margin:0;line-height:1.4;">{kind} #{p.number} in {_esc(p.repo)}</p>'
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


def _section_work_log(context: DigestContext) -> str:
    if context.work_log:
        items = []
        for w in context.work_log:
            sub = f"{_esc(w.repo)} &middot; {w.commits} commit{'' if w.commits == 1 else 's'}"
            items.append(
                f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin-bottom:24px;"><tr>'
                f'<td valign="middle" style="padding-right:24px;">'
                f'<div style="width:32px;height:32px;background-color:{_CHIP_BG};'
                f'border:1px solid {_HAIR};border-radius:4px;text-align:center;line-height:32px;'
                f'font-family:{_MONO};font-size:13px;color:{_MUTED};">{_log_glyph(w.headline)}</div></td>'
                f'<td valign="middle">'
                f'<p style="font-family:{_SANS};font-size:14px;font-weight:700;color:{_INK};margin:0;line-height:1.4;">{_esc(w.headline)}</p>'
                f'<p style="font-family:{_SANS};font-size:11px;color:{_MUTED};margin:1px 0 0;">{sub}</p>'
                f'</td></tr></table>')
        content = "".join(items)
    else:
        content = (f'<p style="font-family:{_SANS};font-size:14px;color:{_MUTED};margin:0;">'
                   f'No commits recorded in this period.</p>')
    return f'{_label("5", "Today\'s Work")}{_rule()}<div style="padding-top:24px;">{content}</div>'


# ── Section 6 — Last 7 days (stat strip) ─────────────────────────

def _stat(label: str, value, delta_key: str, context: DigestContext) -> str:
    if delta_key:
        d = _delta(context.deltas.get(delta_key, 0))
    else:
        d = f'<span style="font-family:{_MONO};font-size:9px;color:{_MUTED};">&mdash;</span>'
    return (f'<td align="center" valign="top" width="16%" style="padding:0 4px;">'
            f'<div style="font-family:{_SERIF};font-size:28px;font-weight:700;color:{_INK};line-height:1.2;margin-bottom:4px;">{value}</div>'
            f'<div style="font-family:{_MONO};font-size:8px;font-weight:500;color:{_MUTED};letter-spacing:0.05em;">{label}</div>'
            f'<div style="margin-top:8px;">{d}</div></td>')


def _section_stats(context: DigestContext) -> str:
    # "DAY STREAK" with the word STREAK in orange — no separate delta line (redundant).
    streak_label = f'DAY <span style="color:{_STREAK};">STREAK</span>'
    strip = (
        f'<table width="100%" role="presentation" cellpadding="0" cellspacing="0"><tr>'
        f'{_stat("PRS OPENED", context.prs_opened, "prs_opened", context)}'
        f'{_stat("PRS MERGED", context.prs_merged, "prs_merged", context)}'
        f'{_stat("REVIEWS GIVEN", context.reviews, "reviews", context)}'
        f'{_stat("ISSUES OPENED", context.issues_opened, "issues_opened", context)}'
        f'{_stat("REPOS ACTIVE", len(context.repos_active), "", context)}'
        f'{_stat(streak_label, context.streak_days, "", context)}'
        f'</tr></table>')
    return f'{_label("6", "Last 7 Days")}{_rule()}<div style="padding-top:32px;">{strip}</div>'


# ── Footer ───────────────────────────────────────────────────────

def _footer() -> str:
    dash = _safe_url(f"{settings.frontend_url}/dashboard")
    return f"""
    {_rule()}
    <table width="100%" role="presentation" cellpadding="0" cellspacing="0" style="margin-top:32px;"><tr>
      <td valign="top" width="55%">
        <p style="font-family:{_SANS};font-size:13px;font-weight:700;font-style:italic;color:{_BRAND};margin:0;">Private by design.</p>
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
                       period_start: str, period_end: str) -> str:
    masthead = f"""
    <table width="100%" role="presentation" cellpadding="0" cellspacing="0">
      <tr>
        <td valign="bottom">
          <div style="font-family:{_SERIF};font-size:32px;font-weight:700;color:{_INK};letter-spacing:-0.02em;line-height:1;">DEVPULSE</div>
        </td>
        <td valign="bottom" align="right" style="white-space:nowrap;">
          <div style="font-family:{_MONO};font-size:12px;font-weight:500;color:{_INK};letter-spacing:0.1em;">ISSUE 001 &middot; DAILY BRIEF</div>
        </td>
      </tr>
      <tr>
        <td valign="top" style="padding-top:4px;">
          <div style="font-family:{_MONO};font-size:9px;font-weight:500;color:{_MUTED};letter-spacing:0.05em;white-space:nowrap;">A DEVELOPER'S DAILY BRIEF</div>
          <div style="font-family:{_MONO};font-size:9px;font-weight:500;color:{_MUTED};letter-spacing:0.05em;white-space:nowrap;margin-top:2px;">BUILT ON YOUR GITHUB</div>
        </td>
        <td valign="top" align="right" style="padding-top:4px;white-space:nowrap;">
          <div style="font-family:{_MONO};font-size:10px;font-weight:500;color:{_MUTED};letter-spacing:0.05em;">{_fmt_date(period_end)} &middot; 8:00 AM</div>
        </td>
      </tr>
    </table>"""

    gap = '<div style="height:48px;line-height:48px;font-size:0;">&nbsp;</div>'
    body = f"""
  <table width="640" role="presentation" cellpadding="0" cellspacing="0" align="center"
         bgcolor="{_BG}" style="max-width:640px;margin:0 auto;background-color:{_BG};">
    <tr><td style="padding:0;">
      <div style="border:1px solid {_HAIR};">
      <div style="padding:32px 32px 16px;">{masthead}</div>
      <div style="margin:0 32px;">{_rule()}</div>
      <div style="padding:40px 32px;">
      {_section_summary(digest, context)}{gap}
      {_section_shipped(context)}{gap}
      {_section_wip_attention(context)}{gap}
      {_section_work_log(context)}{gap}
      {_section_stats(context)}
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
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600;1,700&family=Playfair+Display:wght@700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {{ color-scheme: dark; supported-color-schemes: dark; }}
  body {{ margin:0; padding:0; -webkit-text-size-adjust:100%; background:{_BG}; }}
</style>
</head>
<body bgcolor="{_BG}" style="margin:0;padding:24px 12px;background-color:{_BG};">
{body}
</body>
</html>"""


async def send_digest_email(to: str, subject: str, digest: DigestResult,
                            context: DigestContext, period_start: str, period_end: str) -> bool:
    """Send a digest email via Resend. Returns True on success, False on failure."""
    try:
        resend.api_key = settings.resend_api_key
        payload = {
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": _build_digest_html(digest, context, period_start, period_end),
        }
        if settings.email_reply_to:
            payload["reply_to"] = settings.email_reply_to
        resend.Emails.send(payload)
        return True
    except Exception as e:
        logger.error("[email] failed to send digest to %s: %s", to, e)
        return False
