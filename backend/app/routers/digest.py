"""
DevPulse — Digest Router
GET  /api/digest/settings
POST /api/digest/settings
GET  /api/digest/history
POST /api/digest/preview     (rate limited)
POST /api/digest/send-now    (rate limited)
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request
from app.dependencies import get_current_user
from app.database import get_supabase
from app.schemas import DigestSettingsRequest
from app.services.digest import build_context, generate_and_deliver
from app.services.ai import generate_digest
from app.rate_limit import limiter

router = APIRouter(prefix="/api/digest", tags=["digest"])


@router.get("/settings")
async def get_digest_settings(user: dict = Depends(get_current_user)):
    """Get the user's digest preferences."""
    return {
        "digest_frequency": user.get("digest_frequency", "daily"),
        "digest_day": user.get("digest_day", "monday"),
        "tracked_repos": user.get("tracked_repos"),
    }


@router.post("/settings")
async def update_digest_settings(body: DigestSettingsRequest, user: dict = Depends(get_current_user)):
    """Update the user's digest preferences."""
    supabase = get_supabase()
    update_data = {
        "digest_frequency": body.digest_frequency,
        "digest_day": body.digest_day or "monday",
    }
    if body.tracked_repos is not None:
        update_data["tracked_repos"] = body.tracked_repos

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


@router.post("/preview")
@limiter.limit("10/minute")
async def preview_digest(request: Request, user: dict = Depends(get_current_user)):
    """Preview the next digest without sending it."""
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=7)).isoformat()
    ctx = await build_context(user, start, now.isoformat())
    digest = await generate_digest(ctx)
    return {"digest": digest.model_dump(),
            "period_start": ctx.period_start, "period_end": ctx.period_end}


@router.post("/send-now")
@limiter.limit("5/minute")
async def send_digest_now(request: Request, user: dict = Depends(get_current_user)):
    """Generate a digest immediately, persist it, and email it to the user."""
    return await generate_and_deliver(user, days_back=7)
