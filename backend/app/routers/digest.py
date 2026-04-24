"""
DevPulse — Digest Router
GET  /api/digest/settings
POST /api/digest/settings
GET  /api/digest/history
POST /api/digest/preview
POST /api/digest/send-now
"""

import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.middleware.auth import get_current_user
from app.database import get_supabase
from app.schemas import DigestSettingsRequest
from app.services.digest import build_digest_payload
from app.services.gemini import generate_digest
from app.services.email import send_digest_email

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
async def preview_digest(user: dict = Depends(get_current_user)):
    """Preview the next digest without sending it."""
    payload = await build_digest_payload(user)
    digest_result = await generate_digest(**payload)
    return {
        "digest": digest_result,
        "period_start": payload["period_start"],
        "period_end": payload["period_end"],
    }


@router.post("/send-now")
async def send_digest_now(user: dict = Depends(get_current_user)):
    """Trigger an immediate digest generation and email send."""
    payload = await build_digest_payload(user)
    digest_result = await generate_digest(**payload)

    supabase = get_supabase()
    supabase.table("digests").insert({
        "user_id": user["id"],
        "period_start": payload["period_start"][:10],
        "period_end": payload["period_end"][:10],
        "activity_data": payload,
        "ai_summary": json.dumps(digest_result),
    }).execute()

    email_sent = await send_digest_email(
        to=user["email"],
        subject=f"DevPulse Digest — {digest_result.get('headline', 'Your Activity Summary')}",
        digest=digest_result,
        period_start=payload["period_start"][:10],
        period_end=payload["period_end"][:10],
    )

    if email_sent:
        supabase.table("digests").update(
            {"email_sent_at": datetime.now(timezone.utc).isoformat()}
        ).eq("user_id", user["id"]).eq("period_end", payload["period_end"][:10]).execute()

    return {"message": "Digest sent" if email_sent else "Digest saved but email failed", "digest": digest_result}
