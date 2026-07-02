"""
DevPulse — Digest Orchestration

Builds a typed DigestContext from GitHub, generates the digest via the LLM layer, persists
it, and emails it. `run_all()` is the cron entrypoint and is reused by the manual send-now
route so there is a single delivery path.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from app.schemas import DigestContext, WaitingPR
from app.clients import github, clerk
from app.services.ai import generate_digest
from app.services.email import send_digest_email
from app.database import get_supabase

logger = logging.getLogger("devpulse.digest")

_DELTA_KEYS = ("commits", "prs_opened", "issues_opened", "reviews")


def _period(days_back: int) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=days_back)).isoformat(), now.isoformat()


def _previous_counts(user_id: str) -> dict:
    """Most recent stored digest's activity, for week-over-week deltas."""
    supabase = get_supabase()
    r = (supabase.table("digests").select("activity_data")
         .eq("user_id", user_id).order("created_at", desc=True).limit(1).execute())
    return (r.data[0].get("activity_data") or {}) if r.data else {}


async def build_context(user: dict, period_start: str, period_end: str) -> DigestContext:
    username = user.get("github_username")
    token = user.get("github_access_token")
    if not username or not token:
        raise ValueError("Missing GitHub credentials for user")

    contrib = await github.fetch_contributions(username, token, period_start, period_end)
    waiting = await github.fetch_waiting_prs(username, token)
    prev = _previous_counts(user["id"])
    deltas = {k: contrib[k] - int(prev.get(k, 0)) for k in _DELTA_KEYS}

    return DigestContext(
        github_username=username,
        period_start=period_start[:10], period_end=period_end[:10],
        commits=contrib["commits"], prs_opened=contrib["prs_opened"],
        prs_merged=contrib["prs_merged"], issues_opened=contrib["issues_opened"],
        reviews=contrib["reviews"], repos_active=contrib["repos_active"],
        streak_days=contrib["streak_days"],
        waiting_prs=[WaitingPR(**w) for w in waiting],
        deltas=deltas,
    )


async def generate_and_deliver(user: dict, days_back: int = 7) -> dict:
    """Build context -> generate digest -> persist -> email. Returns a result summary."""
    start, end = _period(days_back)
    context = await build_context(user, start, end)
    digest = await generate_digest(context)

    supabase = get_supabase()
    summary_blob = {"headline": digest.headline, "momentum": digest.momentum,
                    "context": context.model_dump()}
    supabase.table("digests").upsert({
        "user_id": user["id"],
        "period_start": context.period_start,
        "period_end": context.period_end,
        "activity_data": context.model_dump(),
        "ai_summary": json.dumps(summary_blob),
    }, on_conflict="user_id,period_end").execute()

    n_waiting = len(context.waiting_prs)
    subject = (f"DevPulse · {n_waiting} PRs need you · {context.period_end}"
               if n_waiting else f"DevPulse · Daily summary · {context.period_end}")
    sent = await send_digest_email(
        to=user["email"], subject=subject, digest=digest, context=context,
        period_start=context.period_start, period_end=context.period_end,
    )
    if sent:
        supabase.table("digests").update(
            {"email_sent_at": datetime.now(timezone.utc).isoformat()}
        ).eq("user_id", user["id"]).eq("period_end", context.period_end).execute()

    return {"digest": digest.model_dump(), "email_sent": sent,
            "period_start": context.period_start, "period_end": context.period_end}


async def run_all() -> dict:
    """Cron batch. Weekly users only on their digest_day. Per-user error isolation."""
    supabase = get_supabase()
    today = datetime.now(timezone.utc).strftime("%A").lower()
    users = (supabase.table("users").select("*").neq("digest_frequency", "off")
             .execute().data or [])
    processed = sent = failed = 0
    for user in users:
        try:
            freq = user.get("digest_frequency")
            if freq == "weekly" and user.get("digest_day", "monday") != today:
                continue
            # Fetch a live GitHub token for this user (not stored on the row).
            user["github_access_token"] = await clerk.fetch_github_token(user["clerk_id"])
            days_back = 7 if freq == "weekly" else 1
            result = await generate_and_deliver(user, days_back)
            processed += 1
            sent += 1 if result["email_sent"] else 0
        except Exception as e:
            failed += 1
            logger.error("[digest] failed for %s: %s", user.get("email"), e)
    return {"processed": processed, "sent": sent, "failed": failed}
