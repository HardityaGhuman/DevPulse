import pytest
from fastapi import HTTPException
from app.config import settings
from app.security import clerk_jwt
from tests.conftest import make_token, _async


@pytest.mark.asyncio
async def test_rejects_wrong_issuer(monkeypatch, rsa_keys):
    priv, jwks = rsa_keys
    settings.clerk_issuer = "https://good.clerk.dev"
    monkeypatch.setattr(clerk_jwt, "_get_jwks", lambda force=False: _async(jwks))
    token = make_token(priv, iss="https://evil.example.com")
    with pytest.raises(HTTPException) as e:
        await clerk_jwt.verify_clerk_jwt(token)
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_accepts_valid_token(monkeypatch, rsa_keys):
    priv, jwks = rsa_keys
    settings.clerk_issuer = "https://good.clerk.dev"
    monkeypatch.setattr(clerk_jwt, "_get_jwks", lambda force=False: _async(jwks))
    token = make_token(priv, iss="https://good.clerk.dev")
    claims = await clerk_jwt.verify_clerk_jwt(token)
    assert claims["sub"] == "user_123"


@pytest.mark.asyncio
async def test_unset_issuer_fails_closed(monkeypatch, rsa_keys):
    """An empty CLERK_ISSUER must 503, never authenticate — jose skips the issuer check when
    it is None, so a misconfigured deploy would otherwise accept any signable token."""
    priv, jwks = rsa_keys
    settings.clerk_issuer = ""
    monkeypatch.setattr(clerk_jwt, "_get_jwks", lambda force=False: _async(jwks))
    token = make_token(priv, iss="https://anything.example.com")
    with pytest.raises(HTTPException) as e:
        await clerk_jwt.verify_clerk_jwt(token)
    assert e.value.status_code == 503
    settings.clerk_issuer = "https://good.clerk.dev"
