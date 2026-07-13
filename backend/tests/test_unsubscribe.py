import pytest
from fastapi import HTTPException
from app.config import settings
from app.security.unsub_token import make_token, verify_token
from app.services import email as email_svc
from app.routers import unsubscribe as unsub_router
from tests.test_email import CTX, RES


def test_token_roundtrips():
    settings.unsubscribe_secret = "s3cret"
    assert verify_token(make_token("user-1")) == "user-1"


def test_token_rejects_forgery():
    """The token is the ONLY authorization on a public endpoint — a tampered id must not verify."""
    settings.unsubscribe_secret = "s3cret"
    good = make_token("user-1")
    sig = good.split(".", 1)[1]
    import base64
    other = base64.urlsafe_b64encode(b"user-2").decode().rstrip("=")
    assert verify_token(f"{other}.{sig}") is None      # swapped id, kept signature
    assert verify_token("garbage") is None
    assert verify_token(good[:-2]) is None             # truncated signature


def test_token_rejects_other_secret():
    settings.unsubscribe_secret = "s3cret"
    token = make_token("user-1")
    settings.unsubscribe_secret = "different"
    assert verify_token(token) is None
    settings.unsubscribe_secret = "s3cret"


def test_one_click_headers_present_with_token():
    settings.unsubscribe_secret = "s3cret"
    settings.api_base_url = "https://api.example.com"
    h = email_svc._unsubscribe_headers(make_token("user-1"))
    assert h["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert h["List-Unsubscribe"].startswith("<https://api.example.com/api/unsubscribe/")


def test_no_one_click_claim_without_api_base_url():
    """Claiming one-click for a URL that only serves a page is worse than not claiming it."""
    settings.api_base_url = ""
    h = email_svc._unsubscribe_headers(make_token("user-1"))
    assert "List-Unsubscribe-Post" not in h
    assert "List-Unsubscribe" in h


def test_footer_link_matches_one_click_url():
    """Gmail cross-checks the visible footer link against the header — they must agree."""
    settings.unsubscribe_secret = "s3cret"
    settings.api_base_url = "https://api.example.com"
    token = make_token("user-1")
    html = email_svc._build_digest_html(RES, CTX, "2026-07-01", "2026-07-02",
                                        unsub_token=token)
    assert f"https://api.example.com/api/unsubscribe/{token}" in html


@pytest.mark.asyncio
async def test_endpoint_sets_frequency_off(monkeypatch):
    settings.unsubscribe_secret = "s3cret"
    calls = []

    class _T:
        def update(self, payload):
            calls.append(payload)
            return self

        def eq(self, col, val):
            calls.append((col, val))
            return self

        def execute(self):
            return None

    monkeypatch.setattr(unsub_router, "get_supabase",
                        lambda: type("S", (), {"table": lambda self, n: _T()})())

    assert await unsub_router.unsubscribe_one_click(make_token("user-1")) == {"unsubscribed": True}
    assert {"digest_frequency": "off"} in calls
    assert ("id", "user-1") in calls


@pytest.mark.asyncio
async def test_endpoint_rejects_bad_token():
    settings.unsubscribe_secret = "s3cret"
    with pytest.raises(HTTPException) as e:
        await unsubscribe_bad()
    assert e.value.status_code == 400


async def unsubscribe_bad():
    return await unsub_router.unsubscribe_one_click("not-a-real-token")
