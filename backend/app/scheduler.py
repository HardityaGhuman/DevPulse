"""
DevPulse — APScheduler Background Scheduler
Runs daily digest job at 08:00 UTC.
"""

import logging
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database import get_supabase
from app.services.digest import build_digest_payload
from app.services.gemini import generate_digest
from app.services.email import send_digest_email

logger = logging.getLogger("devpulse.scheduler")

scheduler = AsyncIOScheduler()


async def run_digest_job():
    """
    Daily digest job:
    1. Query users with digest_frequency != 'off'
    2. Filter weekly users by matching digest_day
    3. For each: fetch activity → Gemini digest → save → email
    """
    logger.info("[Scheduler] Starting digest job...")
    supabase = get_supabase()
    today = datetime.now(timezone.utc)
    day_name = today.strftime("%A").lower()

    try:
        result = supabase.table("users").select("*").neq("digest_frequency", "off").execute()
        users = result.data or []
    except Exception as e:
        logger.error(f"[Scheduler] Failed to fetch users: {e}")
        return

    for user in users:
        try:
            # Skip weekly users if today isn't their digest day
            if user.get("digest_frequency") == "weekly" and user.get("digest_day", "monday") != day_name:
                continue

            # Determine period
            days_back = 7 if user.get("digest_frequency") == "weekly" else 1
            period_start = (today - timedelta(days=days_back)).isoformat()
            period_end = today.isoformat()

            # Build payload and generate digest
            payload = await build_digest_payload(user, period_start, period_end)
            digest_result = await generate_digest(**payload)

            # Save to database
            supabase.table("digests").insert({
                "user_id": user["id"],
                "period_start": period_start[:10],
                "period_end": period_end[:10],
                "activity_data": payload,
                "ai_summary": str(digest_result),
            }).execute()

            # Send email
            subject = f"DevPulse Digest — {digest_result.get('headline', 'Your Activity Summary')}"
            email_sent = await send_digest_email(
                to=user["email"],
                subject=subject,
                digest=digest_result,
                period_start=period_start[:10],
                period_end=period_end[:10],
            )

            if email_sent:
                supabase.table("digests").update(
                    {"email_sent_at": datetime.now(timezone.utc).isoformat()}
                ).eq("user_id", user["id"]).eq("period_end", period_end[:10]).execute()

            logger.info(f"[Scheduler] Digest sent to {user['email']} (email: {email_sent})")

        except Exception as e:
            logger.error(f"[Scheduler] Failed for user {user.get('email')}: {e}")

    logger.info("[Scheduler] Digest job complete.")


def start_scheduler():
    """Register cron job and start the scheduler."""
    scheduler.add_job(
        run_digest_job,
        "cron",
        hour=8,
        minute=0,
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[Scheduler] Started — daily digest at 08:00 UTC")


def stop_scheduler():
    """Shutdown the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped")
