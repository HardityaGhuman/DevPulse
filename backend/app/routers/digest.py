"""
DevPulse — Digest Router
GET  /api/digest/settings
POST /api/digest/settings
GET  /api/digest/history

NOTE: there is intentionally NO on-demand send/preview route. The digest is only ever delivered
by the scheduled cron pipeline (see routers/internal.py). Exposing an authenticated on-demand
send would be a cost-abuse surface (LLM + email spend) with no product use — deleted 2026-07-11.
"""

from fastapi import APIRouter, Depends, Request
from app.dependencies import get_current_user
from app.database import get_supabase
from app.schemas import DigestSettingsRequest
from app.rate_limit import limiter

router = APIRouter(prefix="/api/digest", tags=["digest"])


@router.get("/settings")
async def get_digest_settings(user: dict = Depends(get_current_user)):
    """Get the user's digest preferences."""
    return {
        "digest_frequency": user.get("digest_frequency", "off"),
        "tracked_repos": user.get("tracked_repos"),
        "digest_hour": user.get("digest_hour"),
        "digest_day": user.get("digest_day"),
        "digest_timezone": user.get("digest_timezone"),
    }


@router.post("/settings")
@limiter.limit("30/minute")
async def update_digest_settings(request: Request, body: DigestSettingsRequest,
                                 user: dict = Depends(get_current_user)):
    """Update the user's digest preferences."""
    supabase = get_supabase()
    update_data = {"digest_frequency": body.digest_frequency}
    if body.tracked_repos is not None:
        update_data["tracked_repos"] = body.tracked_repos
    if body.digest_hour is not None:
        update_data["digest_hour"] = body.digest_hour
    if body.digest_day is not None:
        update_data["digest_day"] = body.digest_day
    if body.digest_timezone is not None:
        update_data["digest_timezone"] = body.digest_timezone

    supabase.table("users").update(update_data).eq("id", user["id"]).execute()
    return {"message": "Settings updated", **update_data}


@router.get("/history")
async def get_digest_history(user: dict = Depends(get_current_user)):
    """Get the user's past digests."""
    supabase = get_supabase()
    result = (
        supabase.table("digests")
        .select("id, period_start, period_end, ai_summary, email_sent_at, created_at")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    return {"digests": result.data or []}
