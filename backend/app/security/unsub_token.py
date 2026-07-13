"""
Unsubscribe tokens.

Gmail's bulk-sender rules require one-click unsubscribe: a `List-Unsubscribe` HTTPS URL plus
`List-Unsubscribe-Post`, which Gmail POSTs on the user's behalf — with no cookie, no session,
no auth. So the URL itself has to carry proof of who it belongs to.

A token is `{user_id}.{hmac_sha256(user_id)}`, base64url-encoded, constant-time compared. It is
capability-scoped: the ONLY thing it can do is set that user's cadence to `off`. It never
expires — a link in a year-old email must still work, which is exactly what the rules intend.
It leaks nothing (the id is opaque) and cannot be forged without the secret.
"""

import hmac
import hashlib
import base64
from app.config import settings


def _secret() -> bytes:
    # Dedicated secret when set; otherwise reuse the cron secret so an existing deploy still has
    # a real key rather than silently signing with an empty string.
    return (settings.unsubscribe_secret or settings.internal_cron_secret).encode()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(user_id: str) -> str:
    sig = hmac.new(_secret(), user_id.encode(), hashlib.sha256).digest()
    return f"{_b64(user_id.encode())}.{_b64(sig)}"


def verify_token(token: str) -> str | None:
    """Return the user_id the token was minted for, or None if it doesn't verify."""
    if not token or not _secret():
        return None
    # Every decode stays inside the try: this endpoint is public and unauthenticated, so a
    # malformed token is an expected input, not an error — it must return None, never raise.
    try:
        raw_id, raw_sig = token.split(".", 1)
        user_id = _unb64(raw_id).decode()
        sig = _unb64(raw_sig)
        expected = hmac.new(_secret(), user_id.encode(), hashlib.sha256).digest()
    except Exception:
        return None
    if not hmac.compare_digest(sig, expected):
        return None
    return user_id
