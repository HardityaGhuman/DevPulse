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
