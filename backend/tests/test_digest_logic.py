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


# ── anchored interval frequencies (6h/12h fire at hours aligned to digest_hour) ──
# NOW = 2026-07-02 12:00 UTC.  anchor 6, 6h -> sends 06/12/18/00 (12 is a send hour).
def test_is_due_6h_at_anchor_hour_never_sent():
    assert d._is_due(_u(freq="6h", digest_hour=6, digest_timezone="UTC"), None, NOW) is True


def test_is_due_6h_off_anchor_hour():
    # anchor 8 -> sends 08/14/20/02; 12:00 is not a send hour -> not due
    assert d._is_due(_u(freq="6h", digest_hour=8, digest_timezone="UTC"), None, NOW) is False


def test_is_due_6h_at_anchor_after_previous_window():
    u = _u(freq="6h", digest_hour=12, digest_timezone="UTC")   # sends 12/18/00/06
    assert d._is_due(u, NOW - timedelta(hours=6), NOW) is True


def test_is_due_6h_at_anchor_when_cron_ran_late_in_previous_window():
    # Previous send landed at 06:20 (cron tick a little past its slot). The 12:00 slot is a new
    # window, so it fires — no elapsed-time threshold to fall short of.
    u = _u(freq="6h", digest_hour=12, digest_timezone="UTC")
    assert d._is_due(u, NOW - timedelta(hours=5, minutes=40), NOW) is True


def test_is_due_6h_not_twice_in_same_window():
    # Two cron ticks inside the same anchored hour must produce exactly one send.
    u = _u(freq="6h", digest_hour=12, digest_timezone="UTC")
    second_tick = datetime(2026, 7, 2, 12, 45, tzinfo=timezone.utc)
    already_sent = datetime(2026, 7, 2, 12, 5, tzinfo=timezone.utc)
    assert d._is_due(u, already_sent, second_tick) is False


def test_is_due_12h_fires_at_new_anchor_soon_after_previous_send():
    """Moving digest_hour must not swallow the first send on the new schedule.

    Regression: the due-check used to require `interval - 30min` of elapsed time since
    last_digest_at — a value produced under the OLD anchor. A 12h user last sent at 13:00 IST
    who moves their anchor to midnight is only 11h past that send when midnight arrives, so
    they were silently skipped. Windows, not elapsed hours, decide.
    """
    u = _u(freq="12h", digest_hour=0, digest_timezone="Asia/Kolkata")
    last = datetime(2026, 7, 13, 7, 30, 56, tzinfo=timezone.utc)    # 13:00 IST, old anchor
    midnight_ist = datetime(2026, 7, 13, 18, 30, tzinfo=timezone.utc)  # 00:00 IST, new anchor
    assert (midnight_ist - last) < timedelta(hours=11, minutes=30)   # under the old guard
    assert d._is_due(u, last, midnight_ist) is True


def test_is_due_6h_respects_timezone_anchor():
    # 12:00 UTC == 17:30 IST -> local hour 17; anchor 5 -> sends 05/11/17/23 -> due
    ist = _u(freq="6h", digest_hour=5, digest_timezone="Asia/Kolkata")
    assert d._is_due(ist, None, NOW) is True


def test_is_due_12h_two_anchored_sends():
    u = _u(freq="12h", digest_hour=0, digest_timezone="UTC")   # sends 00 and 12
    assert d._is_due(u, None, NOW) is True                     # 12:00 is a send hour
    off = _u(freq="12h", digest_hour=1, digest_timezone="UTC") # sends 01 and 13
    assert d._is_due(off, None, NOW) is False


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


def test_weekly_fires_after_moving_the_day_earlier():
    # Same anchor-change bug in the weekly branch: last send Friday (Jul 3 is not yet reached,
    # so use the prior week's Friday), user moves the day to Thursday -> the Thursday that is
    # only 6 days later must still fire. Old code required >= 6 days AND would drop a same-week
    # move; the window check fires because it is a new ISO week.
    thu = _u(freq="weekly", digest_hour=12, digest_day="thursday", digest_timezone="UTC")
    last_friday = datetime(2026, 6, 26, 12, 0, tzinfo=timezone.utc)   # ISO week 26
    assert d._is_due(thu, last_friday, NOW) is True                   # NOW = Thu Jul 2, week 27


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


class _FakeTable:
    """Records the update payloads a table receives; select() returns `rows`."""

    def __init__(self, name, rows, log):
        self.name, self.rows, self.log = name, rows, log

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def update(self, payload):
        self.log.append((self.name, payload))
        return self

    def execute(self):
        return type("R", (), {"data": self.rows})()


class _FakeSupabase:
    def __init__(self, users, log):
        self.users, self.log = users, log

    def table(self, name):
        return _FakeTable(name, self.users if name == "users" else [], self.log)


@pytest.mark.asyncio
async def test_failed_user_still_stamps_last_digest_at(monkeypatch):
    """A revoked GitHub token must not leave the user permanently 'due' — otherwise the hourly
    cron re-enqueues them forever. The failure path stamps last_digest_at, then re-raises so
    Cloud Tasks still retries this enqueue."""
    log = []
    user = {"id": "u1", "clerk_id": "c1", "email": "me@x.com"}
    monkeypatch.setattr(d, "get_supabase", lambda: _FakeSupabase([user], log))

    async def _boom(clerk_id):
        raise RuntimeError("token revoked")

    monkeypatch.setattr(d.clerk, "fetch_github_token", _boom)

    with pytest.raises(RuntimeError):
        await d.process_single_user("u1")

    assert [t for t, p in log] == ["users"]
    assert "last_digest_at" in log[0][1]
