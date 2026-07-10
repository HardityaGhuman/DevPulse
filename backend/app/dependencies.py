"""
Authenticated-user dependency.

Verifies the Clerk JWT, provisions a local user row on first sight, and attaches a live
GitHub token for the duration of the request. The token is held in memory only and is
never written to the database.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest.exceptions import APIError
from app.security.clerk_jwt import verify_clerk_jwt
from app.clients import clerk
from app.database import get_supabase

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    claims = await verify_clerk_jwt(credentials.credentials)
    clerk_id = claims["sub"]
    supabase = get_supabase()

    result = supabase.table("users").select("*").eq("clerk_id", clerk_id).execute()
    user = result.data[0] if result and result.data else None

    clerk_user = None
    if user is None:
        # First authenticated request for this Clerk user — provision a local row.
        clerk_user = await clerk.fetch_user(clerk_id)
        email = claims.get("email") or clerk.primary_email_from_user(clerk_user or {})
        if not email:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "User missing an email address")
        # The dashboard fires several requests in parallel on first load; on a brand-new user
        # they all SELECT-miss and then race to INSERT. One wins; the rest hit the clerk_id
        # unique constraint (Postgres 23505). Also races the Clerk webhook. Treat a duplicate
        # as "someone else provisioned it" and re-select, instead of 500-ing the loser requests.
        try:
            inserted = supabase.table("users").insert({
                "clerk_id": clerk_id,
                "email": email,
                "github_username": clerk.github_username_from_user(clerk_user or {}),
            }).execute()
            user = inserted.data[0] if inserted.data else None
        except APIError as e:
            if getattr(e, "code", None) != "23505":
                raise
            user = None  # lost the provisioning race — the row now exists; fall through to re-select
        if user is None:
            refetch = supabase.table("users").select("*").eq("clerk_id", clerk_id).execute()
            if not refetch.data:
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to provision user")
            user = refetch.data[0]

    # Backfill github_username if still missing (no token needed).
    if not user.get("github_username"):
        clerk_user = clerk_user or await clerk.fetch_user(clerk_id)
        username = clerk.github_username_from_user(clerk_user or {})
        if username:
            supabase.table("users").update(
                {"github_username": username}
            ).eq("id", user["id"]).execute()
            user["github_username"] = username

    # Live GitHub token — memory only, never persisted.
    user["github_access_token"] = await clerk.fetch_github_token(clerk_id)
    return user
