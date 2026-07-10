"""
DevPulse — Digest Orchestration

Builds a typed DigestContext from GitHub, generates the digest via the LLM layer, persists
it, and emails it. A single global cron calls `run_all()`, which sends to each user whose
interval has elapsed. Generated digests are cached on the users row (short TTL) so dashboard
previews don't re-hit the LLM.
"""

import os
import json
import structlog
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import BackgroundTasks
from app.schemas import DigestContext, DigestResult, WaitingPR, ShippedPR, WorkItem
from app.clients import github, clerk
from app.services.ai import generate_digest
from app.services.email import send_digest_email
from app.database import get_supabase

try:
    from google.cloud import tasks_v2
except ImportError:
    tasks_v2 = None

logger = structlog.get_logger("devpulse.digest")

_DELTA_KEYS = ("commits", "prs_opened", "prs_merged", "issues_opened", "reviews")
_INTERVAL_HOURS = {"6h": 6, "12h": 12, "daily": 24, "weekly": 168}
_CACHE_TTL = timedelta(hours=1)
_DUE_GRACE = timedelta(minutes=30)
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_DEFAULT_HOUR = 8


def _interval_hours(freq: str) -> int | None:
    return _INTERVAL_HOURS.get(freq or "")


def _parse_ts(value) -> datetime | None:
    """Parse a Supabase ISO timestamp (handles trailing Z)."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _is_due(user: dict, last: datetime | None, now: datetime) -> bool:
    """Whether this user should receive a digest at `now` (UTC).

    6h/12h are pure intervals (time-of-day doesn't apply). daily/weekly fire at the user's
    chosen hour (and weekday) in their timezone — so the cron MUST run at least hourly.
    """
    freq = user.get("digest_frequency")

    if freq in ("6h", "12h"):
        hours = _INTERVAL_HOURS[freq]
        if last is None:
            return True
        return (now - last) >= (timedelta(hours=hours) - _DUE_GRACE)

    if freq not in ("daily", "weekly"):     # off / unknown
        return False

    try:
        tz = ZoneInfo(user.get("digest_timezone") or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    local = now.astimezone(tz)
    hour = user.get("digest_hour")
    if local.hour != (_DEFAULT_HOUR if hour is None else int(hour)):
        return False

    if freq == "weekly":
        day = (user.get("digest_day") or "monday").lower()
        if _WEEKDAYS[local.weekday()] != day:
            return False
        return last is None or (now - last) >= timedelta(days=6)

    # daily — at most once per local calendar day
    return last is None or last.astimezone(tz).date() < local.date()


def _period_key(user: dict, now: datetime) -> str:
    """Stable identity for the current digest window: distinct per window, identical across
    retries within it.

    Backs both idempotent delivery (a Cloud Tasks retry after a successful send finds the same
    key already marked sent and skips) and interval-aware history — a 6h digest gets 4 keys a
    day, 12h two, daily one, weekly one — replacing the old date-only key that collided for
    sub-daily cadences. Bucketed in the user's own timezone so it aligns with `_is_due`.
    """
    freq = user.get("digest_frequency") or "daily"
    try:
        tz = ZoneInfo(user.get("digest_timezone") or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    local = now.astimezone(tz)
    if freq in ("6h", "12h"):
        block = local.hour // _INTERVAL_HOURS[freq]
        return f"{freq}:{local.date().isoformat()}:{block}"
    if freq == "weekly":
        iso = local.isocalendar()
        return f"weekly:{iso[0]}-W{iso[1]:02d}"
    return f"daily:{local.date().isoformat()}"


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

    # Scope the whole digest to the user's tracked repos when they've picked any; empty/None
    # means whole-account (default). GitHub's contributions API can't repo-filter its totals,
    # so the client re-derives scoped counts via search — see fetch_contributions.
    tracked = user.get("tracked_repos") or None
    contrib = await github.fetch_contributions(username, token, period_start, period_end, tracked=tracked)
    waiting = await github.fetch_waiting_prs(username, token, tracked=tracked)
    merged = await github.fetch_merged_prs(username, token, period_start, tracked=tracked)
    work = await github.fetch_work_log(username, token, period_start, tracked=tracked)

    # contributionsCollection can't report merged PRs — override its placeholder 0 with the
    # honest search count so the "Shipped" stat and its delta are real.
    contrib["prs_merged"] = merged["count"]
    prev = _previous_counts(user["id"])
    deltas = {k: contrib[k] - int(prev.get(k, 0)) for k in _DELTA_KEYS}

    # "Last 7 Days" stat strip is a FIXED trailing week, not the digest window — so a 6h/12h
    # digest doesn't show its tiny window counts under a "Last 7 Days" heading. Separate fetch
    # over [period_end - 7d, period_end]; streak is untouched (365-day lookback in the client).
    week_start = (github.parse_iso(period_end) - timedelta(days=7)).isoformat()
    wc = await github.fetch_contributions(username, token, week_start, period_end, tracked=tracked)
    wm = await github.fetch_merged_prs(username, token, week_start, tracked=tracked)
    week_stats = {
        "prs_opened": wc["prs_opened"], "prs_merged": wm["count"],
        "reviews": wc["reviews"], "issues_opened": wc["issues_opened"],
        "repos_active": len(wc["repos_active"]),
    }

    return DigestContext(
        github_username=username,
        period_start=period_start[:10], period_end=period_end[:10],
        commits=contrib["commits"], prs_opened=contrib["prs_opened"],
        prs_merged=contrib["prs_merged"], issues_opened=contrib["issues_opened"],
        reviews=contrib["reviews"], repos_active=contrib["repos_active"],
        streak_days=contrib["streak_days"],
        waiting_prs=[WaitingPR(**w) for w in waiting],
        shipped_prs=[ShippedPR(**p) for p in merged["prs"]],
        work_log=[WorkItem(**w) for w in work],
        deltas=deltas,
        week_stats=week_stats,
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
    """Generate (fresh) -> persist history -> email -> stamp last_digest_at.

    Idempotent per digest window: Cloud Tasks delivers at-least-once, so if a prior attempt for
    THIS window already recorded a successful send, a retry skips instead of double-emailing.
    """
    supabase = get_supabase()
    now = datetime.now(timezone.utc)
    period_key = _period_key(user, now)

    prior = (supabase.table("digests").select("email_sent_at")
             .eq("user_id", user["id"]).eq("period_key", period_key).limit(1).execute())
    if prior.data and prior.data[0].get("email_sent_at"):
        return {"skipped": "already_sent", "period_key": period_key, "email_sent": True}

    result, context = await get_or_build_digest(user, force=True)

    summary_blob = {"headline": result.headline, "momentum": result.momentum,
                    "context": context.model_dump()}
    supabase.table("digests").upsert({
        "user_id": user["id"],
        "period_key": period_key,
        "period_start": context.period_start,
        "period_end": context.period_end,
        "activity_data": context.model_dump(),
        "ai_summary": json.dumps(summary_blob),
    }, on_conflict="user_id,period_key").execute()

    # Subject leads with the AI headline: unique every run, so Gmail treats each digest as its
    # own message instead of threading same-subject sends and trimming the repeats behind "…".
    head = " ".join(result.headline.split()).strip()  # collapse any stray whitespace/newlines
    if len(head) > 90:
        head = head[:89].rstrip() + "…"
    subject = f"DevPulse · {head}" if head else f"DevPulse · Daily brief · {context.period_end}"
    sent = await send_digest_email(
        to=user["email"], subject=subject, digest=result, context=context,
        period_start=context.period_start, period_end=context.period_end,
        timezone=user.get("digest_timezone"),
    )

    stamp = datetime.now(timezone.utc)
    if sent:
        supabase.table("digests").update({"email_sent_at": stamp.isoformat()}) \
            .eq("user_id", user["id"]).eq("period_key", period_key).execute()
    # Stamp regardless of delivery so undeliverable users don't regenerate every cron tick.
    supabase.table("users").update({"last_digest_at": stamp.isoformat()}) \
        .eq("id", user["id"]).execute()

    return {"digest": result.model_dump(), "email_sent": sent,
            "period_start": context.period_start, "period_end": context.period_end}


async def process_single_user(user_id: str) -> dict:
    """Worker task: Generate and send digest for one user."""
    supabase = get_supabase()
    user_resp = supabase.table("users").select("*").eq("id", user_id).execute()
    if not user_resp.data:
        raise ValueError(f"User {user_id} not found")
    user = user_resp.data[0]
    
    try:
        user["github_access_token"] = await clerk.fetch_github_token(user["clerk_id"])
        result = await generate_and_deliver(user)
        return {"user_id": user_id, "sent": result["email_sent"]}
    except Exception as e:
        logger.error("[digest] failed for %s: %s", user.get("email"), e, exc_info=True)
        raise


async def _process_isolated(user_id: str) -> None:
    """BackgroundTasks entrypoint — MUST NOT propagate.

    Starlette runs background tasks sequentially in one coroutine; a raised exception aborts
    every task queued after it. On the cron fan-out that means a single broken user (bad
    token, GitHub error, LLM outage) would silently block every user ordered after them, on
    every tick. Swallow here so each user is independent. The GCP Cloud Tasks path keeps the
    raising `process_single_user` so a non-2xx triggers a per-user retry instead.
    """
    try:
        await process_single_user(user_id)
    except Exception:
        pass  # already logged with traceback inside process_single_user


def _enqueue_gcp_task(user_id: str, base_url: str):
    """Enqueue a task to GCP Cloud Tasks."""
    client = tasks_v2.CloudTasksClient()
    project = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GCP_LOCATION")
    queue = os.environ.get("GCP_QUEUE_NAME")
    
    if not all([project, location, queue]):
        raise ValueError("Missing GCP Tasks environment variables")
        
    parent = client.queue_path(project, location, queue)
    
    secret = os.environ.get("INTERNAL_CRON_SECRET", "")
    # Cloud Run terminates TLS at its proxy, so request.base_url comes back as http://. If the
    # task targets http://, Cloud Run 302-redirects to https and that redirect DOWNGRADES the
    # POST to a GET -> our POST-only worker returns 405 and the digest never runs. Force https.
    url = f"{base_url}/internal/digest/{user_id}"
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"X-Internal-Secret": secret},
        }
    }
    client.create_task(request={"parent": parent, "task": task})

async def run_all(background_tasks: BackgroundTasks, base_url: str) -> dict:
    """Cron batch: Enqueue tasks for each non-off user whose interval has elapsed. Per-user isolation."""
    supabase = get_supabase()
    now = datetime.now(timezone.utc)
    users = (supabase.table("users").select("*").neq("digest_frequency", "off")
             .execute().data or [])
             
    enqueued = 0
    use_gcp = os.environ.get("USE_GCP_TASKS", "false").lower() == "true"
    
    for user in users:
        if not _is_due(user, _parse_ts(user.get("last_digest_at")), now):
            continue
            
        if use_gcp and tasks_v2:
            try:
                _enqueue_gcp_task(user["id"], base_url)
            except Exception as e:
                logger.error("Failed to enqueue GCP task for %s: %s", user["id"], e)
                background_tasks.add_task(_process_isolated, user["id"])
        else:
            background_tasks.add_task(_process_isolated, user["id"])
            
        enqueued += 1
        
    return {"enqueued": enqueued, "queue_type": "gcp_tasks" if use_gcp else "background_tasks"}
