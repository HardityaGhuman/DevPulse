"""
Clerk JWT verification.

Verifies the RS256 signature against Clerk's JWKS, enforces the issuer, caches keys with
a TTL, and refetches once on an unknown `kid` (key rotation). Errors are generic so no
library internals leak to the client.
"""

import time
import logging
import httpx
from fastapi import HTTPException, status
from jose import jwt, JWTError
from app.config import settings

logger = logging.getLogger("devpulse.auth")

_JWKS_TTL = 3600  # seconds
_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0


async def _get_jwks(force: bool = False) -> dict:
    """Return Clerk's JWKS, using a TTL cache. `force` bypasses the cache."""
    global _jwks_cache, _jwks_fetched_at
    fresh = _jwks_cache is not None and (time.time() - _jwks_fetched_at) < _JWKS_TTL
    if fresh and not force:
        return _jwks_cache
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(settings.clerk_jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_fetched_at = time.time()
    return _jwks_cache


def _find_key(jwks: dict, kid: str | None) -> dict | None:
    return next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)


async def verify_clerk_jwt(token: str) -> dict:
    """Return decoded claims, or raise HTTPException(401). Never leak internals."""
    # Fail CLOSED on a missing issuer. jose silently SKIPS the issuer check when `issuer=None`,
    # so an empty CLERK_ISSUER env would accept any token another Clerk instance signed with a
    # key our JWKS URL happens to serve. Misconfiguration must 503, never authenticate.
    if not settings.clerk_issuer:
        logger.error("[auth] CLERK_ISSUER is not set — refusing to verify tokens")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Auth service unavailable")

    try:
        kid = jwt.get_unverified_header(token).get("kid")
        jwks = await _get_jwks()
        key = _find_key(jwks, kid)
        if key is None:  # possible key rotation — refetch once
            jwks = await _get_jwks(force=True)
            key = _find_key(jwks, kid)
        if key is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authentication")

        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            # Clerk session tokens carry the app in `azp`, not always `aud`; the issuer
            # check is the strong guarantee. Enable audience if you set it in a JWT template.
            options={"verify_aud": False},
        )
        if not claims.get("sub"):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authentication")
        return claims
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authentication")
    except httpx.HTTPError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Auth service unavailable")
