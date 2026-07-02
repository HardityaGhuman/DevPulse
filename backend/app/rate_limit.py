"""
Per-user rate limiting via slowapi.

Keys on a slice of the bearer token when present (so limits are per authenticated user),
falling back to client IP. In-memory storage is per-instance — approximate under multiple
Cloud Run instances, which is acceptable for a personal tool.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _user_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    return auth[-32:] if auth else get_remote_address(request)


limiter = Limiter(key_func=_user_key)
