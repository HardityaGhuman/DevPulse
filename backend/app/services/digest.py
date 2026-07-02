"""
DevPulse — Digest Orchestration

Builds a typed DigestContext from GitHub, generates the digest via the LLM layer, persists
it, and emails it. A single global cron calls `run_all()`, which sends to each user whose
interval has elapsed. Generated digests are cached on the users row (short TTL) so dashboard
previews don't re-hit the LLM.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from app.schemas import DigestContext, DigestResult, WaitingPR
from app.clients import github, clerk
from app.services.ai import generate_digest
from app.services.email import send_digest_email
from app.database import get_supabase

logger = logging.getLogger("devpulse.digest")

_DELTA_KEYS = ("commits", "prs_opened", "issues_opened", "reviews")
_INTERVAL_HOURS = {"6h": 6, "12h": 12, "daily": 24, "weekly": 168}
_CACHE_TTL = timedelta(hours=1)
_DUE_GRACE = timedelta(minutes=30)


def _interval_hours(freq: str) -> int | None:
    return _INTERVAL_HOURS.get(freq or "")


def _parse_ts(value) -> datetime | None:
    """Parse a Supabase ISO timestamp (handles trailing Z)."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _is_due(freq: str, last_digest_at: datetime | None, now: datetime) -> bool:
    hours = _interval_hours(freq)
    if hours is None:                       # off / unknown
        return False
    if last_digest_at is None:
        return True
    return (now - last_digest_at) >= (timedelta(hours=hours) - _DUE_GRACE)


def _cache_fresh(cached_at: datetime | None, now: datetime) -> bool:
    return cached_at is not None and (now - cached_at) < _CACHE_TTL


def _previous_counts(user_id: str) -> dict:
    """Most recent stored digest's activity, for period-over-period deltas."""
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


async def get_or_build_digest(user: dict, force: bool = False):
    """Return (DigestResult, DigestContext). Reuse the users-row cache when fresh unless
    force=True. Always writes the cache when it generates."""
    now = datetime.now(timezone.utc)
    if not force and _cache_fresh(_parse_ts(user.get("cached_at")), now):
        blob = user.get("cached_digest") or {}
        if blob.get("result") and blob.get("context"):
            return DigestResult(**blob["result"]), DigestContext(**blob["context"])

    hours = _interval_hours(user.get("digest_frequency")) or 24
    start = (now - timedelta(hours=hours)).isoformat()
    context = await build_context(user, start, now.isoformat())
    result = await generate_digest(context)

    get_supabase().table("users").update({
        "cached_digest": {"result": result.model_dump(), "context": context.model_dump()},
        "cached_at": now.isoformat(),
    }).eq("id", user["id"]).execute()
    return result, context


async def generate_and_deliver(user: dict) -> dict:
    """Generate (fresh) -> persist history -> email -> stamp last_digest_at."""
    result, context = await get_or_build_digest(user, force=True)
    supabase = get_supabase()

    summary_blob = {"headline": result.headline, "momentum": result.momentum,
                    "context": context.model_dump()}
    supabase.table("digests").upsert({
        "user_id": user["id"],
        "period_start": context.period_start,
        "period_end": context.period_end,
        "activity_data": context.model_dump(),
        "ai_summary": json.dumps(summary_blob),
    }, on_conflict="user_id,period_end").execute()

    n = len(context.waiting_prs)
    noun = "PR needs" if n == 1 else "PRs need"
    subject = (f"DevPulse · {n} {noun} you · {context.period_end}"
               if n else f"DevPulse · Activity summary · {context.period_end}")
    sent = await send_digest_email(
        to=user["email"], subject=subject, digest=result, context=context,
        period_start=context.period_start, period_end=context.period_end,
    )

    now = datetime.now(timezone.utc)
    if sent:
        supabase.table("digests").update({"email_sent_at": now.isoformat()}) \
            .eq("user_id", user["id"]).eq("period_end", context.period_end).execute()
    # Stamp regardless of delivery so undeliverable users don't regenerate every cron tick.
    supabase.table("users").update({"last_digest_at": now.isoformat()}) \
        .eq("id", user["id"]).execute()

    return {"digest": result.model_dump(), "email_sent": sent,
            "period_start": context.period_start, "period_end": context.period_end}


async def run_all() -> dict:
    """Cron batch: send to each non-off user whose interval has elapsed. Per-user isolation."""
    supabase = get_supabase()
    now = datetime.now(timezone.utc)
    users = (supabase.table("users").select("*").neq("digest_frequency", "off")
             .execute().data or [])
    processed = sent = failed = 0
    for user in users:
        try:
            if not _is_due(user.get("digest_frequency"),
                           _parse_ts(user.get("last_digest_at")), now):
                continue
            user["github_access_token"] = await clerk.fetch_github_token(user["clerk_id"])
            result = await generate_and_deliver(user)
            processed += 1
            sent += 1 if result["email_sent"] else 0
        except Exception as e:
            failed += 1
            logger.error("[digest] failed for %s: %s", user.get("email"), e)
    return {"processed": processed, "sent": sent, "failed": failed}
