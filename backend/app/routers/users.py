"""
DevPulse — Users Router
POST /api/users/sync   (Clerk webhook, no auth)
GET  /api/users/me
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from app.middleware.auth import get_current_user
from app.database import get_supabase

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/sync")
async def sync_user(request: Request):
    """
    Clerk webhook endpoint — creates or updates a user record
    when Clerk fires user.created or user.updated events.
    """
    body = await request.json()
    event_type = body.get("type", "")
    data = body.get("data", {})

    if event_type not in ("user.created", "user.updated"):
        return {"message": "Event ignored"}

    clerk_id = data.get("id")
    if not clerk_id:
        raise HTTPException(status_code=400, detail="Missing clerk user ID")

    # Extract email
    email_addresses = data.get("email_addresses", [])
    primary_email = next(
        (e["email_address"] for e in email_addresses if e.get("id") == data.get("primary_email_address_id")),
        email_addresses[0]["email_address"] if email_addresses else None,
    )

    if not primary_email:
        raise HTTPException(status_code=400, detail="No email found in webhook data")

    # Extract GitHub username from external accounts
    external_accounts = data.get("external_accounts", [])
    github_username = None
    github_access_token = None
    for account in external_accounts:
        if account.get("provider") == "oauth_github":
            github_username = account.get("username")
            break

    supabase = get_supabase()

    # Upsert user
    user_data = {
        "clerk_id": clerk_id,
        "email": primary_email,
        "github_username": github_username,
    }

    existing = supabase.table("users").select("id").eq("clerk_id", clerk_id).maybe_single().execute()

    if existing.data:
        supabase.table("users").update(user_data).eq("clerk_id", clerk_id).execute()
    else:
        supabase.table("users").insert(user_data).execute()

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
        "tracked_repos": user.get("tracked_repos"),
        "created_at": user.get("created_at"),
    }
