"""
Authenticated-user dependency.

Verifies the Clerk JWT, provisions a local user row on first sight, and attaches a live
GitHub token for the duration of the request. The token is held in memory only and is
never written to the database.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
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
        inserted = supabase.table("users").insert({
            "clerk_id": clerk_id,
            "email": email,
            "github_username": clerk.github_username_from_user(clerk_user or {}),
        }).execute()
        if not inserted.data:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to provision user")
        user = inserted.data[0]

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
