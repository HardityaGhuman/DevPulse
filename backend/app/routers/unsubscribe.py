"""
DevPulse — Unsubscribe Router

The one surface that is intentionally UNAUTHENTICATED: Gmail POSTs the List-Unsubscribe URL
itself, with no user session. Authorization comes from the HMAC in the token (see
`security/unsub_token.py`), and the only thing the endpoint can do is set that one user's
cadence to `off` — it reads nothing back and cannot touch any other row.

POST = Gmail/Outlook one-click (required by the 2024 bulk-sender rules).
GET  = a human clicking the Unsubscribe link in the footer; same effect, plus a page to look at.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse
from app.config import settings
from app.database import get_supabase
from app.security.unsub_token import verify_token

router = APIRouter(prefix="/api", tags=["unsubscribe"])


def _turn_off(token: str) -> None:
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid unsubscribe link")
    get_supabase().table("users").update({"digest_frequency": "off"}).eq("id", user_id).execute()


@router.post("/unsubscribe/{token}")
async def unsubscribe_one_click(token: str):
    """Mail-client one-click target. Must 200 fast and never redirect."""
    _turn_off(token)
    return {"unsubscribed": True}


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe_link(token: str):
    _turn_off(token)
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Unsubscribed — DevPulse</title></head>
<body style="margin:0;background:#FFFFFF;color:#1A1C1C;
             font-family:'Inter',-apple-system,'Helvetica Neue',Arial,sans-serif;">
  <div style="max-width:520px;margin:0 auto;padding:96px 24px;">
    <p style="font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:0.1em;
              color:#71717A;margin:0 0 24px;">DEVPULSE</p>
    <h1 style="font-family:'Playfair Display',Georgia,serif;font-size:40px;font-weight:700;
               line-height:1.15;margin:0 0 16px;">You're unsubscribed.</h1>
    <p style="font-size:17px;line-height:1.6;color:#1A1C1C;margin:0 0 32px;">
      No more digests. Your account and settings are untouched — turn delivery back on any time
      from the dashboard.</p>
    <a href="{settings.frontend_url}/dashboard"
       style="display:inline-block;background:#1A1C1C;color:#FFFFFF;text-decoration:none;
              padding:14px 28px;border-radius:999px;font-size:14px;">Open dashboard</a>
  </div>
</body></html>""")
