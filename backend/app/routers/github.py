"""
DevPulse — GitHub Router
GET /api/github/repos
GET /api/github/activity
"""

from fastapi import APIRouter, Depends, HTTPException
from app.middleware.auth import get_current_user
from app.services.github import fetch_user_repos, fetch_recent_activity

router = APIRouter(prefix="/api/github", tags=["github"])


@router.get("/repos")
async def get_repos(user: dict = Depends(get_current_user)):
    """Fetch the authenticated user's GitHub repositories."""
    access_token = user.get("github_access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub access token not configured")

    repos = await fetch_user_repos(access_token)
    return {"repos": repos}


@router.get("/activity")
async def get_activity(days: int = 7, user: dict = Depends(get_current_user)):
    """Fetch recent GitHub activity for the authenticated user."""
    access_token = user.get("github_access_token")
    github_username = user.get("github_username")

    if not access_token or not github_username:
        raise HTTPException(status_code=400, detail="GitHub credentials not configured")

    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    activity = await fetch_recent_activity(github_username, access_token, since)
    return activity
