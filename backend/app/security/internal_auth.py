"""Shared-secret guard for the Cloud Scheduler cron endpoint.

Cloud Scheduler sends `X-Internal-Secret`; we compare it to INTERNAL_CRON_SECRET in
constant time. An unset secret rejects everything (fail closed).
"""

import secrets
from fastapi import Header, HTTPException, status
from app.config import settings


async def require_internal_secret(x_internal_secret: str = Header(...)) -> bool:
    expected = settings.internal_cron_secret
    if not expected or not secrets.compare_digest(x_internal_secret, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid internal secret")
    return True
