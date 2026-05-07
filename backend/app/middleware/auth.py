"""
DevPulse — Clerk JWT Authentication Middleware
Verifies Clerk JWTs using JWKS and attaches user info to request state.
"""

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from app.config import settings
from app.database import get_supabase

security = HTTPBearer()

_jwks_cache: dict | None = None


def _github_username_from_clerk_user(user_data: dict) -> str | None:
    """Extract the GitHub username from a Clerk user payload."""
    for account in user_data.get("external_accounts", []):
        if account.get("provider") in ("oauth_github", "github"):
            return account.get("username")
    return None


async def _fetch_clerk_user(clerk_id: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.clerk.com/v1/users/{clerk_id}",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"}
        )
        if response.status_code == 200:
            return response.json()
    return None


async def _fetch_clerk_github_token(clerk_id: str) -> str | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.clerk.com/v1/users/{clerk_id}/oauth_access_tokens/oauth_github",
            headers={"Authorization": f"Bearer {settings.clerk_secret_key}"}
        )
        if response.status_code != 200:
            return None

    tokens = response.json()
    if tokens and isinstance(tokens, list):
        return tokens[0].get("token")
    return None


async def _get_jwks() -> dict:
    """Fetch and cache Clerk JWKS keys."""
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.clerk_jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
    return _jwks_cache


def _get_signing_key(token: str, jwks: dict) -> dict:
    """Extract the correct signing key from JWKS based on the token's kid."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    for key in jwks.get("keys", []):
        if key["kid"] == kid:
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unable to find matching signing key",
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency that verifies the Clerk JWT and returns the user record.
    Attach this to any protected route.
    """
    token = credentials.credentials

    try:
        jwks = await _get_jwks()
        signing_key = _get_signing_key(token, jwks)

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        clerk_id = payload.get("sub")
        if not clerk_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )

        # Look up user in database
        supabase = get_supabase()
        result = (
            supabase.table("users")
            .select("*")
            .eq("clerk_id", clerk_id)
            .execute()
        )

        user = result.data[0] if result and result.data else None
        if not user:
            # Auto-provision users who are authenticated in Clerk but missing locally.
            email = payload.get("email")
            if not email:
                user_data = await _fetch_clerk_user(clerk_id)
                if user_data:
                    email_addresses = user_data.get("email_addresses", [])
                    primary_email_id = user_data.get("primary_email_address_id")
                    primary_email = next(
                        (e.get("email_address") for e in email_addresses if e.get("id") == primary_email_id),
                        email_addresses[0].get("email_address") if email_addresses else None,
                    )
                    email = primary_email

            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Authenticated user is missing an email address",
                )

            inserted = (
                supabase.table("users")
                .insert({"clerk_id": clerk_id, "email": email})
                .execute()
            )
            if not inserted or not inserted.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to provision user profile",
                )
            user = inserted.data[0]

        # Auto-fetch GitHub profile/token if missing. This keeps digest generation
        # working even when the Clerk webhook did not populate the local user row.
        github_updates = {}
        if not user.get("github_username"):
            clerk_user = await _fetch_clerk_user(clerk_id)
            github_username = _github_username_from_clerk_user(clerk_user or {})
            if github_username:
                github_updates["github_username"] = github_username

        if not user.get("github_access_token"):
            github_token = await _fetch_clerk_github_token(clerk_id)
            if github_token:
                github_updates["github_access_token"] = github_token

        if github_updates:
            supabase.table("users").update(github_updates).eq("id", user["id"]).execute()
            user.update(github_updates)

        return user

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify authentication",
        )
