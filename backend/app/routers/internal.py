"""
DevPulse — Internal Router
POST /internal/run-digests   (cron target, shared-secret protected)

Called by Google Cloud Scheduler on a schedule. Not part of the public API.
"""

from fastapi import APIRouter, Depends, BackgroundTasks, Request
from app.security.internal_auth import require_internal_secret
from app.services.digest import run_all, process_single_user

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/run-digests")
async def run_digests(
    request: Request,
    background_tasks: BackgroundTasks,
    _: bool = Depends(require_internal_secret)
):
    """Cron target: Fan out to all eligible users using Cloud Tasks or BackgroundTasks."""
    # Pass request to reconstruct the base URL for Cloud Tasks webhooks
    base_url = str(request.base_url).rstrip("/")
    return await run_all(background_tasks, base_url)

@router.post("/digest/{user_id}")
async def run_single_digest(
    user_id: str,
    _: bool = Depends(require_internal_secret)
):
    """Task target: Process digest for a single user."""
    return await process_single_user(user_id)
