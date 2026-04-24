"""
DevPulse — Review Router
POST /api/review/code
POST /api/review/pr
GET  /api/review/history
GET  /api/review/{id}
GET  /api/review/share/{token}  (public)
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from app.middleware.auth import get_current_user
from app.database import get_supabase
from app.schemas import CodeReviewRequest, PRReviewRequest
from app.services.gemini import review_code, review_pr
from app.services.github import fetch_pr_diff, parse_pr_url

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("/code")
async def create_code_review(body: CodeReviewRequest, user: dict = Depends(get_current_user)):
    """Submit code for AI review."""
    result = await review_code(body.code, body.language)
    share_token = str(uuid.uuid4())

    supabase = get_supabase()
    record = supabase.table("reviews").insert({
        "user_id": user["id"],
        "type": "code",
        "input_content": body.code,
        "language": body.language,
        "review_result": result,
        "share_token": share_token,
    }).execute()

    return {
        "id": record.data[0]["id"],
        "type": "code",
        "review_result": result,
        "share_token": share_token,
        "language": body.language,
        "created_at": record.data[0]["created_at"],
    }


@router.post("/pr")
async def create_pr_review(body: PRReviewRequest, user: dict = Depends(get_current_user)):
    """Submit a GitHub PR URL for AI review."""
    try:
        owner, repo, pr_number = parse_pr_url(body.pr_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    access_token = user.get("github_access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub access token not configured")

    pr_data = await fetch_pr_diff(owner, repo, pr_number, access_token)
    result = await review_pr(pr_data["title"], pr_data["description"], pr_data["diff"])
    share_token = str(uuid.uuid4())

    supabase = get_supabase()
    record = supabase.table("reviews").insert({
        "user_id": user["id"],
        "type": "pr",
        "input_content": pr_data["diff"][:10000],
        "pr_url": body.pr_url,
        "pr_number": pr_number,
        "repo_name": f"{owner}/{repo}",
        "review_result": result,
        "share_token": share_token,
    }).execute()

    return {
        "id": record.data[0]["id"],
        "type": "pr",
        "review_result": result,
        "share_token": share_token,
        "pr_url": body.pr_url,
        "repo_name": f"{owner}/{repo}",
        "created_at": record.data[0]["created_at"],
    }


@router.get("/history")
async def get_review_history(user: dict = Depends(get_current_user)):
    """Get the user's review history."""
    supabase = get_supabase()
    result = (
        supabase.table("reviews")
        .select("id, type, language, pr_url, repo_name, review_result, share_token, created_at")
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    items = []
    for r in result.data or []:
        score = r.get("review_result", {}).get("score")
        items.append({
            "id": r["id"],
            "type": r["type"],
            "language": r.get("language"),
            "pr_url": r.get("pr_url"),
            "repo_name": r.get("repo_name"),
            "score": score,
            "share_token": r.get("share_token"),
            "created_at": r["created_at"],
        })

    return {"reviews": items}


@router.get("/share/{token}")
async def get_shared_review(token: str):
    """Public endpoint — get a shared review by its token."""
    supabase = get_supabase()
    result = (
        supabase.table("reviews")
        .select("id, type, language, pr_url, repo_name, review_result, created_at")
        .eq("share_token", token)
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Review not found")

    return result.data


@router.get("/{review_id}")
async def get_review_detail(review_id: str, user: dict = Depends(get_current_user)):
    """Get a single review by ID (must belong to the authenticated user)."""
    supabase = get_supabase()
    result = (
        supabase.table("reviews")
        .select("*")
        .eq("id", review_id)
        .eq("user_id", user["id"])
        .maybe_single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Review not found")

    return result.data
