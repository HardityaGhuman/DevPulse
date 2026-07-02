"""
DevPulse — Internal Router
POST /internal/run-digests   (cron target, shared-secret protected)

Called by Google Cloud Scheduler on a schedule. Not part of the public API.
"""

from fastapi import APIRouter, Depends
from app.security.internal_auth import require_internal_secret
from app.services.digest import run_all

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/run-digests")
async def run_digests(_: bool = Depends(require_internal_secret)):
    """Generate and send digests for all eligible users."""
    return await run_all()
