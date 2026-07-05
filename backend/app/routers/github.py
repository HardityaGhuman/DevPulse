"""
DevPulse — GitHub Router
GET /api/github/repos       (user's own repos)
GET /api/github/activity    (contribution summary for N days)
"""

from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.dependencies import get_current_user
from app.clients.github import fetch_user_repos, fetch_contributions
from app.rate_limit import limiter

router = APIRouter(prefix="/api/github", tags=["github"])


@router.get("/repos")
@limiter.limit("20/minute")
async def get_repos(request: Request, user: dict = Depends(get_current_user)):
    """Fetch the authenticated user's GitHub repositories (proxies GitHub — rate limited)."""
    access_token = user.get("github_access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub access token not configured")
    return {"repos": await fetch_user_repos(access_token)}


@router.get("/activity")
@limiter.limit("20/minute")
async def get_activity(request: Request, days: int = Query(7, ge=1, le=90),
                       user: dict = Depends(get_current_user)):
    """Fetch a contribution summary for the authenticated user over the last N days."""
    access_token = user.get("github_access_token")
    github_username = user.get("github_username")
    if not access_token or not github_username:
        raise HTTPException(status_code=400, detail="GitHub credentials not configured")

    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).isoformat()
    return await fetch_contributions(github_username, access_token, since, now.isoformat())
