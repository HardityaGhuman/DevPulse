"""
DevPulse — Email Service
Sends digest emails using the Resend SDK with a dark-themed HTML template.
"""

import resend
from app.config import settings

resend.api_key = settings.resend_api_key


def _build_digest_html(digest: dict, period_start: str, period_end: str) -> str:
    """Build a dark-themed inline HTML email for the digest."""
    highlights_html = "".join(
        f'<li style="padding:4px 0;color:#f1f5f9;">{h}</li>'
        for h in digest.get("highlights", [])
    )

    momentum_colors = {"rising": "#22c55e", "steady": "#3b82f6", "declining": "#ef4444"}
    momentum = digest.get("momentum", "steady")
    momentum_color = momentum_colors.get(momentum, "#3b82f6")

    return f"""
    <div style="background:#0a0a0a;padding:32px;font-family:'Inter',system-ui,sans-serif;">
      <div style="max-width:600px;margin:0 auto;background:#111111;border:1px solid #222222;border-radius:8px;padding:32px;">
        <h1 style="color:#f1f5f9;font-size:24px;margin:0 0 8px;">DevPulse Digest</h1>
        <p style="color:#64748b;font-size:14px;margin:0 0 24px;">{period_start} — {period_end}</p>
        <div style="background:#1a1a1a;border:1px solid #222222;border-radius:8px;padding:20px;margin-bottom:24px;">
          <h2 style="color:#3b82f6;font-size:18px;margin:0 0 8px;">📊 {digest.get("headline", "")}</h2>
          <span style="display:inline-block;background:{momentum_color};color:#0a0a0a;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;">
            {momentum.upper()}
          </span>
        </div>
        <div style="margin-bottom:24px;">
          <h3 style="color:#f1f5f9;font-size:16px;margin:0 0 12px;">Highlights</h3>
          <ul style="list-style:none;padding:0;margin:0;">{highlights_html}</ul>
        </div>
        <div style="background:#1a1a1a;border:1px solid #222222;border-radius:8px;padding:16px;margin-bottom:24px;">
          <p style="color:#64748b;font-size:13px;margin:0 0 4px;">🔥 Streak</p>
          <p style="color:#f1f5f9;font-size:14px;margin:0;">{digest.get("streak_comment", "")}</p>
        </div>
        <div style="background:#1a1a1a;border:1px solid #222222;border-radius:8px;padding:16px;margin-bottom:24px;">
          <p style="color:#64748b;font-size:13px;margin:0 0 4px;">💡 Coaching Tip</p>
          <p style="color:#f1f5f9;font-size:14px;margin:0;">{digest.get("coaching_tip", "")}</p>
        </div>
        <p style="color:#64748b;font-size:12px;text-align:center;margin:24px 0 0;">
          Powered by DevPulse · AI-driven developer intelligence
        </p>
      </div>
    </div>
    """


async def send_digest_email(to: str, subject: str, digest: dict, period_start: str, period_end: str) -> bool:
    """Send a digest email via Resend."""
    try:
        html = _build_digest_html(digest, period_start, period_end)
        resend.Emails.send({
            "from": "DevPulse <digest@devpulse.dev>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return True
    except Exception as e:
        print(f"[Email] Failed to send digest to {to}: {e}")
        return False
