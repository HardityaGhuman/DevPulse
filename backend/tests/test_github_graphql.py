import pytest
import respx
import httpx
from datetime import datetime, timedelta, timezone
from app.clients import github

GQL = "https://api.github.com/graphql"


def _day(offset: int, count: int) -> dict:
    """A calendar day `offset` days before today (UTC)."""
    d = datetime.now(timezone.utc).date() - timedelta(days=offset)
    return {"date": d.isoformat(), "contributionCount": count}


def _weeks(days: list[dict]) -> list[dict]:
    return [{"contributionDays": days}]


def test_current_streak_counts_consecutive_days():
    # today, yesterday, day-before all active -> 3
    weeks = _weeks([_day(0, 8), _day(1, 9), _day(2, 3), _day(3, 0), _day(4, 5)])
    assert github._current_streak(weeks) == 3


def test_current_streak_empty_today_does_not_break_yesterday():
    # today has 0 (not pushed yet) but yesterday+ are active -> streak survives
    weeks = _weeks([_day(0, 0), _day(1, 9), _day(2, 4)])
    assert github._current_streak(weeks) == 2


def test_current_streak_ignores_future_padding_days():
    # GitHub pads the current week with future zero-count days; they must not zero the streak
    weeks = _weeks([_day(-2, 0), _day(-1, 0), _day(0, 5), _day(1, 4)])
    assert github._current_streak(weeks) == 2


@pytest.mark.asyncio
@respx.mock
async def test_fetch_contributions_parses_totals():
    payload = {"data": {"user": {"contributionsCollection": {
        "totalCommitContributions": 12,
        "totalPullRequestContributions": 3,
        "totalIssueContributions": 2,
        "totalPullRequestReviewContributions": 4,
        "commitContributionsByRepository": [
            {"repository": {"nameWithOwner": "me/app"}},
            {"repository": {"nameWithOwner": "me/lib"}},
        ],
        "contributionCalendar": {"weeks": [
            {"contributionDays": [{"date": "2026-06-30", "contributionCount": 1}]}
        ]},
    }}}}
    respx.post(GQL).mock(return_value=httpx.Response(200, json=payload))
    out = await github.fetch_contributions("me", "tok", "2026-06-24T00:00:00+00:00",
                                           "2026-07-01T00:00:00+00:00")
    assert out["commits"] == 12
    assert out["prs_opened"] == 3
    assert out["reviews"] == 4
    assert out["streak_days"] == 1
    assert set(out["repos_active"]) == {"me/app", "me/lib"}


@pytest.mark.asyncio
@respx.mock
async def test_streak_stops_at_first_zero_day():
    payload = {"data": {"user": {"contributionsCollection": {
        "totalCommitContributions": 0, "totalPullRequestContributions": 0,
        "totalIssueContributions": 0, "totalPullRequestReviewContributions": 0,
        "commitContributionsByRepository": [],
        "contributionCalendar": {"weeks": [{"contributionDays": [
            {"date": "2026-06-28", "contributionCount": 2},
            {"date": "2026-06-29", "contributionCount": 0},
            {"date": "2026-06-30", "contributionCount": 5},
        ]}]},
    }}}}
    respx.post(GQL).mock(return_value=httpx.Response(200, json=payload))
    out = await github.fetch_contributions("me", "tok", "2026-06-24T00:00:00+00:00",
                                           "2026-07-01T00:00:00+00:00")
    # Most recent day (06-30) has activity, day before (06-29) is zero -> streak = 1
    assert out["streak_days"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_fetch_contributions_raises_on_null_user():
    # Bad login / missing scope -> HTTP 200 with user:null. Must fail loud, not send zeros.
    respx.post(GQL).mock(return_value=httpx.Response(200, json={"data": {"user": None}}))
    with pytest.raises(RuntimeError):
        await github.fetch_contributions("ghost", "tok", "2026-06-24T00:00:00+00:00",
                                         "2026-07-01T00:00:00+00:00")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_contributions_raises_on_graphql_errors():
    respx.post(GQL).mock(return_value=httpx.Response(
        200, json={"errors": [{"message": "Bad credentials"}], "data": {"user": None}}))
    with pytest.raises(RuntimeError):
        await github.fetch_contributions("me", "tok", "2026-06-24T00:00:00+00:00",
                                         "2026-07-01T00:00:00+00:00")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_contributions_scoped_to_tracked_repos():
    # commits summed from per-repo breakdown for tracked repos only; prs/issues/reviews from
    # repo-filtered search issueCount.
    contrib = {"data": {"user": {"contributionsCollection": {
        "totalCommitContributions": 99, "totalPullRequestContributions": 99,
        "totalIssueContributions": 99, "totalPullRequestReviewContributions": 99,
        "commitContributionsByRepository": [
            {"repository": {"nameWithOwner": "me/app"}, "contributions": {"totalCount": 7}},
            {"repository": {"nameWithOwner": "me/other"}, "contributions": {"totalCount": 40}},
        ],
        "contributionCalendar": {"weeks": []},
    }}}}
    streak = {"data": {"user": {"contributionsCollection": {
        "contributionCalendar": {"weeks": []}}}}}
    count = lambda n: {"data": {"search": {"issueCount": n}}}
    route = respx.post(GQL)
    # order: contrib, streak, prs_opened, issues_opened, reviews
    route.side_effect = [httpx.Response(200, json=contrib), httpx.Response(200, json=streak),
                         httpx.Response(200, json=count(2)), httpx.Response(200, json=count(1)),
                         httpx.Response(200, json=count(3))]
    out = await github.fetch_contributions("me", "tok", "2026-06-24T00:00:00+00:00",
                                           "2026-07-01T00:00:00+00:00", tracked=["me/app"])
    assert out["commits"] == 7                     # only me/app, not me/other's 40
    assert out["repos_active"] == ["me/app"]       # me/other excluded
    assert out["prs_opened"] == 2 and out["issues_opened"] == 1 and out["reviews"] == 3


@pytest.mark.asyncio
@respx.mock
async def test_fetch_merged_prs_adds_repo_filter():
    captured = {}
    def handler(request):
        import json as _j
        captured["q"] = _j.loads(request.content)["variables"]["q"]
        return httpx.Response(200, json={"data": {"search": {"issueCount": 0, "nodes": []}}})
    respx.post(GQL).mock(side_effect=handler)
    await github.fetch_merged_prs("me", "tok", "2026-07-02T00:00:00+00:00",
                                  tracked=["me/app", "me/lib"])
    assert "repo:me/app" in captured["q"] and "repo:me/lib" in captured["q"]


@pytest.mark.asyncio
@respx.mock
async def test_fetch_waiting_prs_enriched():
    def node(num, repo):
        return {"number": num, "title": f"PR {num}", "url": f"https://x/{num}",
                "createdAt": "2026-06-20T00:00:00Z", "isDraft": False,
                "mergeable": "CONFLICTING", "additions": 10, "deletions": 2,
                "changedFiles": 3, "repository": {"nameWithOwner": repo}}
    payloads = [
        {"data": {"search": {"nodes": [node(1, "me/app")]}}},   # review-requested
        {"data": {"search": {"nodes": [node(2, "me/lib")]}}},   # authored
    ]
    route = respx.post(GQL)
    route.side_effect = [httpx.Response(200, json=payloads[0]),
                         httpx.Response(200, json=payloads[1])]
    out = await github.fetch_waiting_prs("me", "tok")
    by_num = {p["number"]: p for p in out}
    assert by_num[1]["reason"] == "review_requested"
    assert by_num[1]["mergeable"] == "CONFLICTING"
    assert by_num[1]["changed_files"] == 3
    assert by_num[2]["reason"] == "yours"


@pytest.mark.asyncio
@respx.mock
async def test_fetch_merged_prs_count_and_titles():
    payload = {"data": {"search": {"issueCount": 2, "nodes": [
        {"number": 21, "title": "Memory Persistence", "url": "https://x/21",
         "mergedAt": "2026-07-02T10:00:00Z", "repository": {"nameWithOwner": "me/aria"}},
        {"number": 18, "title": "Eval Pipeline", "url": "https://x/18",
         "mergedAt": "2026-07-02T09:00:00Z", "repository": {"nameWithOwner": "me/aria"}},
    ]}}}
    respx.post(GQL).mock(return_value=httpx.Response(200, json=payload))
    out = await github.fetch_merged_prs("me", "tok", "2026-07-02T00:00:00+00:00")
    assert out["count"] == 2                       # issueCount, not len(nodes) — search caps nodes
    assert [p["number"] for p in out["prs"]] == [21, 18]
    assert out["prs"][0] == {"repo": "me/aria", "number": 21,
                             "title": "Memory Persistence", "url": "https://x/21"}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_work_log_groups_by_headline():
    payload = {"items": [
        {"commit": {"message": "Added memory adapter\n\nlong body ignored"},
         "repository": {"full_name": "me/aria"}},
        {"commit": {"message": "Added memory adapter"}, "repository": {"full_name": "me/aria"}},
        {"commit": {"message": "Refactored agent registry"},
         "repository": {"full_name": "me/aria"}},
    ]}
    respx.get("https://api.github.com/search/commits").mock(
        return_value=httpx.Response(200, json=payload))
    out = await github.fetch_work_log("me", "tok", "2026-07-02T00:00:00+00:00")
    by = {w["headline"]: w for w in out}
    assert by["Added memory adapter"]["commits"] == 2      # grouped, body stripped
    assert by["Added memory adapter"]["repo"] == "me/aria"
    assert by["Refactored agent registry"]["commits"] == 1
