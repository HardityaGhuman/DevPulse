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
