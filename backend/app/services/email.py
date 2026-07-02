"""
DevPulse — Email Service (Resend only)

Renders a clean, light-theme, email-safe digest (inline styles, table layout) and sends it
via Resend. Facts come straight from DigestContext; the LLM contributes only the headline.

The email is a FIXED light theme. It does not follow the recipient's system theme; instead it
locks to light via `color-scheme` meta + explicit bg/text on every element, so dark-mode email
clients cannot auto-invert it into an unreadable mess.
"""

import logging
import resend
from app.config import settings
from app.schemas import DigestResult, DigestContext

logger = logging.getLogger("devpulse.email")

_FONT = "'Inter', -apple-system, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif"
_MOMENTUM = {
    "rising": ("#DCFCE7", "#166534"),
    "steady": ("#DCE2F3", "#151C27"),
    "declining": ("#FEE2E2", "#991B1B"),
}


def _pill(text: str, bg: str, color: str, border: str = "") -> str:
    b = f"border:1px solid {border};" if border else ""
    return (f'<span style="display:inline-block;padding:2px 10px;border-radius:9999px;'
            f'font-size:12px;font-weight:600;background:{bg};color:{color};{b}">{text}</span>')


def _delta(v: int) -> str:
    if v > 0:
        return f'<span style="color:#059669;font-size:12px;">&#8593;{v}</span>'
    if v < 0:
        return f'<span style="color:#E11D48;font-size:12px;">&#8595;{abs(v)}</span>'
    return ""


def _section_header(label: str) -> str:
    return (f'<div style="font-size:13px;font-weight:600;letter-spacing:0.06em;'
            f'text-transform:uppercase;color:#1C1B1B;border-bottom:1px solid #EAEAEA;'
            f'padding-bottom:6px;margin:0 0 16px;">{label}</div>')


def _waiting_rows(context: DigestContext) -> str:
    if not context.waiting_prs:
        return ('<p style="font-size:14px;color:#585F6C;margin:0;">'
                'Nothing needs your review — you\'re clear.</p>')
    rows = []
    for pr in context.waiting_prs:
        pills = []
        if pr.mergeable == "CONFLICTING":
            pills.append(_pill("Conflict", "#FEF3C7", "#92400E"))
        if pr.reason == "review_requested":
            pills.append(_pill("Review requested", "#FFFFFF", "#5B5BD6", border="#5B5BD6"))
        if pr.is_draft:
            pills.append(_pill("Draft", "#DCE2F3", "#151C27"))
        pills_html = "&nbsp;".join(pills)
        rows.append(f"""
        <tr><td style="padding:12px 0;border-bottom:1px solid #EAEAEA;">
          <div style="font-size:14px;color:#1C1B1B;margin:0 0 4px;">
            <span style="color:#585F6C;font-size:12px;">{pr.repo}</span>
            &nbsp;<span style="font-weight:600;"><a href="{pr.url}" style="color:#1C1B1B;text-decoration:none;">{pr.title}</a></span>
          </div>
          <div style="font-size:12px;color:#6B7280;">
            {pr.age_days}d ago &nbsp; <span style="color:#059669;">+{pr.additions}</span>
            &nbsp;<span style="color:#E11D48;">-{pr.deletions}</span>
            &nbsp; {pr.changed_files} files &nbsp; {pills_html}
          </div>
        </td></tr>""")
    return (f'<table width="100%" cellpadding="0" cellspacing="0" role="presentation">'
            f'{"".join(rows)}</table>')


def _stat(label: str, value: int, delta_key: str, context: DigestContext) -> str:
    d = _delta(context.deltas.get(delta_key, 0)) if delta_key else ""
    return (f'<td style="padding:0 8px;vertical-align:top;">'
            f'<div style="font-size:12px;color:#585F6C;margin:0 0 2px;">{label}</div>'
            f'<div style="font-size:24px;font-weight:300;color:#1C1B1B;">{value} {d}</div></td>')


def _repo_chips(context: DigestContext) -> str:
    chips = "".join(
        f'<span style="display:inline-block;margin:0 6px 6px 0;padding:5px 12px;'
        f'border:1px solid #EAEAEA;border-radius:6px;background:#FCF9F8;font-size:13px;'
        f'color:#1C1B1B;">{r}</span>' for r in context.repos_active)
    return chips or '<span style="font-size:13px;color:#585F6C;">No repositories touched.</span>'


def _build_digest_html(digest: DigestResult, context: DigestContext,
                       period_start: str, period_end: str) -> str:
    m_bg, m_fg = _MOMENTUM.get(digest.momentum, _MOMENTUM["steady"])
    momentum_pill = _pill(digest.momentum.upper(), m_bg, m_fg)
    stats = (
        f'<table width="100%" cellpadding="0" cellspacing="0" role="presentation"><tr>'
        f'{_stat("Commits", context.commits, "commits", context)}'
        f'{_stat("PRs opened", context.prs_opened, "prs_opened", context)}'
        f'{_stat("PRs merged", context.prs_merged, "", context)}'
        f'{_stat("Issues", context.issues_opened, "issues_opened", context)}'
        f'{_stat("Reviews", context.reviews, "reviews", context)}'
        f'</tr></table>'
    )
    streak = (f'<div style="margin-top:16px;display:inline-block;background:#FFF7ED;'
              f'border:1px solid #FFEDD5;border-radius:9999px;padding:4px 12px;font-size:13px;'
              f'color:#9A3412;font-weight:600;">&#128293; {context.streak_days}-day streak</div>')

    body = f"""<div style="background:#F5F5F4;padding:32px 12px;font-family:{_FONT};">
  <table width="600" cellpadding="0" cellspacing="0" role="presentation" align="center" style="max-width:600px;margin:0 auto;background:#F5F5F4;">
    <tr><td style="padding:8px 4px 16px;">
      <table width="100%" role="presentation"><tr>
        <td style="font-size:15px;font-weight:700;color:#5B5BD6;">DevPulse</td>
        <td align="right" style="font-size:12px;color:#464553;">{period_start} – {period_end}&nbsp;&nbsp;{momentum_pill}</td>
      </tr></table>
    </td></tr>
    <tr><td style="background:#FFFFFF;border:1px solid #EAEAEA;border-radius:12px;padding:32px;">
      <p style="font-size:15px;color:#1C1B1B;margin:0 0 32px;">{digest.headline}</p>

      <div style="margin-bottom:32px;">
        {_section_header("&#9889; Waiting on you")}
        {_waiting_rows(context)}
      </div>

      <div style="margin-bottom:32px;">
        {_section_header("&#128202; Your activity")}
        {stats}
        {streak}
      </div>

      <div>
        {_section_header("&#128230; Active repositories")}
        {_repo_chips(context)}
      </div>
    </td></tr>
    <tr><td style="padding:24px 4px;text-align:center;font-size:12px;color:#585F6C;">
      <a href="{settings.frontend_url}/settings" style="color:#4241BC;text-decoration:underline;">Manage digest settings</a><br/>
      Generated {period_end} · DevPulse
    </td></tr>
  </table>
</div>"""

    # Full document + color-scheme lock so dark-mode clients can't invert the fixed light theme.
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light only">
<meta name="supported-color-schemes" content="light only">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{ color-scheme: light only; supported-color-schemes: light only; }}
  body {{ margin:0; padding:0; background:#F5F5F4; -webkit-text-size-adjust:100%; font-family:{_FONT}; }}
</style>
</head>
<body style="margin:0;padding:0;background:#F5F5F4;">
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
