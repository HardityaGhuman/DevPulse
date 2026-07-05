"""
DevPulse — Users Router
POST /api/users/sync   (Clerk webhook — Svix signature verified)
GET  /api/users/me
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from app.dependencies import get_current_user
from app.security.webhook import verify_svix
from app.clients import clerk
from app.database import get_supabase

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/sync")
async def sync_user(request: Request):
    """Clerk webhook — creates/updates a user row on user.created / user.updated.
    The request MUST carry a valid Svix signature; unsigned requests are rejected."""
    body = await request.body()
    verify_svix(dict(request.headers), body)  # raises 401 on unsigned/invalid

    payload = await request.json()
    if payload.get("type") not in ("user.created", "user.updated"):
        return {"message": "Event ignored"}

    data = payload.get("data", {})
    clerk_id = data.get("id")
    if not clerk_id:
        raise HTTPException(status_code=400, detail="Missing clerk user ID")

    email = clerk.primary_email_from_user(data)
    if not email:
        raise HTTPException(status_code=400, detail="No email found in webhook data")

    supabase = get_supabase()
    row = {
        "clerk_id": clerk_id,
        "email": email,
        "github_username": clerk.github_username_from_user(data),
    }
    existing = supabase.table("users").select("id").eq("clerk_id", clerk_id).maybe_single().execute()
    if existing.data:
        supabase.table("users").update(row).eq("clerk_id", clerk_id).execute()
    else:
        supabase.table("users").insert(row).execute()

    return {"message": "User synced"}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Get the current authenticated user's profile."""
    return {
        "id": user["id"],
        "clerk_id": user["clerk_id"],
        "email": user["email"],
        "github_username": user.get("github_username"),
        "digest_frequency": user.get("digest_frequency", "daily"),
        "digest_day": user.get("digest_day", "monday"),
        "digest_hour": user.get("digest_hour"),
        "digest_timezone": user.get("digest_timezone"),
        "tracked_repos": user.get("tracked_repos"),
        "created_at": user.get("created_at"),
    }
