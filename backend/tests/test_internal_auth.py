import pytest
from fastapi import HTTPException
from app.config import settings
from app.security.internal_auth import require_internal_secret


@pytest.mark.asyncio
async def test_rejects_bad_secret():
    settings.internal_cron_secret = "right"
    with pytest.raises(HTTPException) as e:
        await require_internal_secret(x_internal_secret="wrong")
    assert e.value.status_code == 401


@pytest.mark.asyncio
async def test_accepts_good_secret():
    settings.internal_cron_secret = "right"
    assert await require_internal_secret(x_internal_secret="right") is True


@pytest.mark.asyncio
async def test_rejects_when_unconfigured():
    settings.internal_cron_secret = ""
    with pytest.raises(HTTPException) as e:
        await require_internal_secret(x_internal_secret="anything")
    assert e.value.status_code == 401
