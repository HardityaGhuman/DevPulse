"""
GitHub data client.

Uses the GraphQL `contributionsCollection` API for accurate activity counts and streaks
(includes private repos, unlike the REST events feed), plus REST search for "waiting" PRs
and a slim repo list for the frontend.
"""

import re
import httpx
from datetime import datetime, timezone

GRAPHQL = "https://api.github.com/graphql"
REST = "https://api.github.com"

_CONTRIB_QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      commitContributionsByRepository(maxRepositories:25) {
        repository { nameWithOwner }
      }
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _current_streak(weeks: list[dict]) -> int:
    """Count consecutive most-recent days with activity."""
    days = [d for w in weeks for d in w.get("contributionDays", [])]
    days.sort(key=lambda d: d["date"], reverse=True)
    streak = 0
    for d in days:
        if d.get("contributionCount", 0) > 0:
            streak += 1
        else:
            break
    return streak


async def fetch_contributions(username: str, token: str, since: str, until: str) -> dict:
    """Fetch accurate contribution counts + streak for the period."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            GRAPHQL,
            headers=_headers(token),
            json={"query": _CONTRIB_QUERY,
                  "variables": {"login": username, "from": since, "to": until}},
        )
        r.raise_for_status()
        cc = (r.json().get("data", {}).get("user", {}) or {}).get("contributionsCollection", {})

    repos = [x["repository"]["nameWithOwner"]
             for x in cc.get("commitContributionsByRepository", [])]
    weeks = cc.get("contributionCalendar", {}).get("weeks", [])
    commits = cc.get("totalCommitContributions", 0)
    prs = cc.get("totalPullRequestContributions", 0)
    issues = cc.get("totalIssueContributions", 0)
    reviews = cc.get("totalPullRequestReviewContributions", 0)
    return {
        "commits": commits,
        "prs_opened": prs,
        "prs_merged": 0,  # not exposed by contributionsCollection; enrich via search later
        "issues_opened": issues,
        "reviews": reviews,
        "repos_active": repos,
        "streak_days": _current_streak(weeks),
        "total_events": commits + prs + issues + reviews,
    }


async def fetch_waiting_prs(username: str, token: str) -> list[dict]:
    """Open PRs authored by the user OR requesting their review — the 'waiting on you' list."""
    authored = f"is:open is:pr author:{username} archived:false"
    review_req = f"is:open is:pr review-requested:{username} archived:false"
    out: list[dict] = []
    async with httpx.AsyncClient(timeout=20) as client:
        for query in (authored, review_req):
            r = await client.get(f"{REST}/search/issues",
                                 headers=_headers(token),
                                 params={"q": query, "per_page": 20})
            if r.status_code != 200:
                continue
            for item in r.json().get("items", []):
                created = parse_iso(item["created_at"])
                age = (datetime.now(timezone.utc) - created).days
                out.append({
                    "repo": re.sub(r"^https://api.github.com/repos/", "",
                                   item.get("repository_url", "")),
                    "number": item.get("number"),
                    "title": item.get("title"),
                    "url": item.get("html_url"),
                    "age_days": age,
                })
    return out


async def fetch_user_repos(token: str) -> list[dict]:
    """Slim REST list of the user's own repos for the frontend."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{REST}/user/repos", headers=_headers(token),
                             params={"sort": "updated", "per_page": 100, "type": "owner"})
        r.raise_for_status()
        return [{
            "name": x["full_name"], "description": x.get("description", ""),
            "language": x.get("language"), "stars": x.get("stargazers_count", 0),
            "updated_at": x.get("updated_at"), "private": x.get("private", False),
            "url": x.get("html_url"),
        } for x in r.json()]
