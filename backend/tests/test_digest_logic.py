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


def _u(**kw):
    return {"digest_frequency": kw.pop("freq", "6h"), **kw}


# ── period key: idempotency / interval-aware identity ──
def test_period_key_6h_distinct_windows_same_retry():
    u = _u(freq="6h", digest_timezone="UTC")
    k0 = d._period_key(u, datetime(2026, 7, 9, 3, 0, tzinfo=timezone.utc))    # window 0 (00-05)
    k1 = d._period_key(u, datetime(2026, 7, 9, 9, 0, tzinfo=timezone.utc))    # window 1 (06-11)
    retry = d._period_key(u, datetime(2026, 7, 9, 4, 30, tzinfo=timezone.utc))  # retry of window 0
    assert k0 != k1              # different 6h windows -> different rows
    assert k0 == retry           # a retry inside the window is idempotent


def test_period_key_daily_and_weekly_stable_within_window():
    daily = _u(freq="daily", digest_timezone="UTC")
    d0 = d._period_key(daily, datetime(2026, 7, 9, 1, 0, tzinfo=timezone.utc))
    d1 = d._period_key(daily, datetime(2026, 7, 9, 23, 0, tzinfo=timezone.utc))
    assert d0 == d1 == "daily:2026-07-09"
    weekly = _u(freq="weekly", digest_timezone="UTC")
    assert d._period_key(weekly, datetime(2026, 7, 9, 8, 0, tzinfo=timezone.utc)).startswith("weekly:2026-W")


def test_period_key_uses_user_timezone():
    # 2026-07-09 02:00 UTC is still 2026-07-08 in US/Pacific -> key must reflect local date
    u = _u(freq="daily", digest_timezone="America/Los_Angeles")
    assert d._period_key(u, datetime(2026, 7, 9, 2, 0, tzinfo=timezone.utc)) == "daily:2026-07-08"


# ── interval frequencies (time-of-day doesn't apply) ──
def test_is_due_never_sent():
    assert d._is_due(_u(freq="6h"), None, NOW) is True


def test_is_due_elapsed_enough():
    assert d._is_due(_u(freq="6h"), NOW - timedelta(hours=6), NOW) is True


def test_is_due_within_grace():
    last = NOW - timedelta(hours=5, minutes=40)   # 5h40 >= 6h-30min -> due
    assert d._is_due(_u(freq="6h"), last, NOW) is True


def test_is_due_too_soon():
    assert d._is_due(_u(freq="6h"), NOW - timedelta(hours=2), NOW) is False


def test_is_due_off_never():
    assert d._is_due(_u(freq="off"), None, NOW) is False


# ── daily/weekly honour hour + timezone + day ──  (NOW = 2026-07-02 12:00 UTC, a Thursday)
def test_daily_due_at_chosen_hour_utc():
    assert d._is_due(_u(freq="daily", digest_hour=12, digest_timezone="UTC"), None, NOW) is True


def test_daily_not_due_off_hour():
    assert d._is_due(_u(freq="daily", digest_hour=13, digest_timezone="UTC"), None, NOW) is False


def test_daily_respects_timezone():
    # 12:00 UTC == 17:30 in Asia/Kolkata -> local hour 17.
    ist = _u(freq="daily", digest_hour=17, digest_timezone="Asia/Kolkata")
    assert d._is_due(ist, None, NOW) is True
    assert d._is_due(_u(freq="daily", digest_hour=12, digest_timezone="Asia/Kolkata"), None, NOW) is False


def test_daily_once_per_day():
    # Right hour, but already sent earlier today -> not due again.
    u = _u(freq="daily", digest_hour=12, digest_timezone="UTC")
    assert d._is_due(u, NOW - timedelta(hours=1), NOW) is False
    assert d._is_due(u, NOW - timedelta(days=1), NOW) is True


def test_weekly_due_on_day_and_hour():
    thu = _u(freq="weekly", digest_hour=12, digest_day="thursday", digest_timezone="UTC")
    assert d._is_due(thu, None, NOW) is True
    fri = _u(freq="weekly", digest_hour=12, digest_day="friday", digest_timezone="UTC")
    assert d._is_due(fri, None, NOW) is False


def test_weekly_not_twice_in_week():
    thu = _u(freq="weekly", digest_hour=12, digest_day="thursday", digest_timezone="UTC")
    assert d._is_due(thu, NOW - timedelta(days=2), NOW) is False
    assert d._is_due(thu, NOW - timedelta(days=7), NOW) is True


def test_cache_fresh():
    assert d._cache_fresh(NOW - timedelta(minutes=30), NOW) is True
    assert d._cache_fresh(NOW - timedelta(hours=2), NOW) is False
    assert d._cache_fresh(None, NOW) is False


def test_settings_rejects_bad_frequency():
    DigestSettingsRequest(digest_frequency="6h")      # ok
    DigestSettingsRequest(digest_frequency="weekly")  # ok
    with pytest.raises(ValidationError):
        DigestSettingsRequest(digest_frequency="3h")


@pytest.mark.asyncio
async def test_build_context_populates_shipped_work_log_and_merged(monkeypatch):
    async def _contrib(*a, **k):
        return {"commits": 5, "prs_opened": 2, "prs_merged": 0, "issues_opened": 1,
                "reviews": 3, "repos_active": ["me/aria"], "streak_days": 8,
                "total_events": 11}
    async def _waiting(*a, **k):
        return []
    async def _merged(*a, **k):
        return {"count": 6, "prs": [{"repo": "me/aria", "number": 21,
                                     "title": "Memory Persistence", "url": "https://x/21"}]}
    async def _worklog(*a, **k):
        return [{"repo": "me/aria", "headline": "Added memory adapter", "commits": 2}]

    monkeypatch.setattr(d.github, "fetch_contributions", _contrib)
    monkeypatch.setattr(d.github, "fetch_waiting_prs", _waiting)
    monkeypatch.setattr(d.github, "fetch_merged_prs", _merged)
    monkeypatch.setattr(d.github, "fetch_work_log", _worklog)
    monkeypatch.setattr(d, "_previous_counts", lambda uid: {"prs_merged": 2})

    user = {"id": "u1", "github_username": "me", "github_access_token": "tok"}
    ctx = await d.build_context(user, "2026-07-02T00:00:00+00:00",
                                "2026-07-02T12:00:00+00:00")
    assert ctx.prs_merged == 6                       # from search, not the contrib 0
    assert ctx.shipped_prs[0].number == 21
    assert ctx.work_log[0].headline == "Added memory adapter"
    assert ctx.deltas["prs_merged"] == 4             # 6 - previous 2
