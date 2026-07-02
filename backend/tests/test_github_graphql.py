import pytest
import respx
import httpx
from app.clients import github

GQL = "https://api.github.com/graphql"


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
