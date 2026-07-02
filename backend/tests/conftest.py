"""Shared test fixtures: an RSA keypair + JWKS and a token minter for JWT tests."""

import pytest
from jose import jwt, jwk


@pytest.fixture(scope="session")
def rsa_keys():
    """Return (private_pem, jwks_dict) for signing/verifying RS256 test tokens."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()

    pub_jwk = jwk.construct(key.public_key(), "RS256").to_dict()
    pub_jwk = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in pub_jwk.items()}
    pub_jwk["kid"] = "test-kid"
    return priv, {"keys": [pub_jwk]}


def make_token(priv, *, iss, sub="user_123", kid="test-kid", aud="devpulse"):
    """Mint a signed RS256 JWT for tests."""
    return jwt.encode(
        {"sub": sub, "iss": iss, "aud": aud},
        priv,
        algorithm="RS256",
        headers={"kid": kid},
    )


async def _async(v):
    """Await-able that just returns v — for monkeypatching async helpers."""
    return v
