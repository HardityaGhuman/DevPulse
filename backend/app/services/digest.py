"""
DevPulse — Digest Builder Service
Assembles GitHub activity data into the format expected by the Gemini digest prompt.
"""

import json
from datetime import datetime, timedelta, timezone
from app.services.github import fetch_recent_activity


async def build_digest_payload(
    user: dict,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict:
    """
    Build the complete digest payload for a user.
    Fetches GitHub activity and formats it for the Gemini prompt.
    """
    if period_end is None:
        period_end = datetime.now(timezone.utc).isoformat()
    if period_start is None:
        period_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    github_username = user.get("github_username")
    access_token = user.get("github_access_token")

    if not github_username or not access_token:
        return {
            "github_username": github_username or "unknown",
            "period_start": period_start,
            "period_end": period_end,
            "activity_json": json.dumps({"error": "Missing GitHub credentials"}),
        }

    activity = await fetch_recent_activity(
        username=github_username,
        access_token=access_token,
        since=period_start,
    )

    return {
        "github_username": github_username,
        "period_start": period_start,
        "period_end": period_end,
        "activity_json": json.dumps(activity, default=str),
    }
