from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError
from app.schemas import DigestSettingsRequest
from app.services import digest as d

NOW = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)


def test_interval_hours():
    assert d._interval_hours("6h") == 6
    assert d._interval_hours("daily") == 24
    assert d._interval_hours("weekly") == 168
    assert d._interval_hours("off") is None
    assert d._interval_hours("bogus") is None


def test_is_due_never_sent():
    assert d._is_due("6h", None, NOW) is True


def test_is_due_elapsed_enough():
    last = NOW - timedelta(hours=6)
    assert d._is_due("6h", last, NOW) is True


def test_is_due_within_grace():
    last = NOW - timedelta(hours=5, minutes=40)   # 5h40 >= 6h-30min -> due
    assert d._is_due("6h", last, NOW) is True


def test_is_due_too_soon():
    last = NOW - timedelta(hours=2)
    assert d._is_due("6h", last, NOW) is False


def test_is_due_off_never():
    assert d._is_due("off", None, NOW) is False


def test_cache_fresh():
    assert d._cache_fresh(NOW - timedelta(minutes=30), NOW) is True
    assert d._cache_fresh(NOW - timedelta(hours=2), NOW) is False
    assert d._cache_fresh(None, NOW) is False


def test_settings_rejects_bad_frequency():
    DigestSettingsRequest(digest_frequency="6h")      # ok
    DigestSettingsRequest(digest_frequency="weekly")  # ok
    with pytest.raises(ValidationError):
        DigestSettingsRequest(digest_frequency="3h")
