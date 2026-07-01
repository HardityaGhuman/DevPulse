"""
Clerk Admin API client.

Fetches user profiles and live GitHub OAuth tokens. GitHub tokens are returned to the
caller for immediate use and are NEVER persisted to the database.
"""

import httpx
from app.config import settings

_BASE = "https://api.clerk.com/v1"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.clerk_secret_key}"}


async def fetch_user(clerk_id: str) -> dict | None:
    """Fetch a Clerk user record, or None if not found/unavailable."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{_BASE}/users/{clerk_id}", headers=_headers())
        return r.json() if r.status_code == 200 else None


async def fetch_github_token(clerk_id: str) -> str | None:
    """Fetch the user's current GitHub OAuth access token from Clerk (not stored)."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{_BASE}/users/{clerk_id}/oauth_access_tokens/oauth_github",
            headers=_headers(),
        )
        if r.status_code != 200:
            return None
        data = r.json()
    if isinstance(data, list) and data:
        return data[0].get("token")
    return None


def github_username_from_user(user_data: dict) -> str | None:
    """Extract the GitHub username from a Clerk user's external accounts."""
    for acct in (user_data or {}).get("external_accounts", []):
        if acct.get("provider") in ("oauth_github", "github"):
            return acct.get("username")
    return None


def primary_email_from_user(user_data: dict) -> str | None:
    """Extract the primary email address from a Clerk user payload."""
    emails = (user_data or {}).get("email_addresses", [])
    primary_id = (user_data or {}).get("primary_email_address_id")
    return next(
        (e.get("email_address") for e in emails if e.get("id") == primary_id),
        emails[0].get("email_address") if emails else None,
    )
