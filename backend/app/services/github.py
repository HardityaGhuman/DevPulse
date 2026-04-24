"""
DevPulse — GitHub API Service
Handles all interactions with the GitHub REST API.
"""

import re
import httpx
from datetime import datetime, timedelta, timezone

GITHUB_API_BASE = "https://api.github.com"


def _headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def fetch_user_repos(access_token: str) -> list[dict]:
    """Fetch the authenticated user's repositories."""
    async with httpx.AsyncClient() as client:
        repos = []
        page = 1
        while True:
            response = await client.get(
                f"{GITHUB_API_BASE}/user/repos",
                headers=_headers(access_token),
                params={"sort": "updated", "per_page": 100, "page": page, "type": "owner"},
            )
            response.raise_for_status()
            data = response.json()
            if not data:
                break
            for repo in data:
                repos.append({
                    "name": repo["full_name"],
                    "description": repo.get("description", ""),
                    "language": repo.get("language"),
                    "stars": repo.get("stargazers_count", 0),
                    "updated_at": repo.get("updated_at"),
                    "private": repo.get("private", False),
                    "url": repo.get("html_url"),
                })
            if len(data) < 100 or page >= 5:
                break
            page += 1
        return repos


async def fetch_pr_diff(owner: str, repo: str, pr_number: int, access_token: str) -> dict:
    """Fetch PR metadata and diff from GitHub."""
    async with httpx.AsyncClient() as client:
        pr_response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=_headers(access_token),
        )
        pr_response.raise_for_status()
        pr_data = pr_response.json()

        diff_headers = _headers(access_token)
        diff_headers["Accept"] = "application/vnd.github.v3.diff"
        diff_response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}",
            headers=diff_headers,
        )
        diff_response.raise_for_status()

        return {
            "title": pr_data.get("title", ""),
            "description": pr_data.get("body", ""),
            "diff": diff_response.text,
            "state": pr_data.get("state"),
            "user": pr_data.get("user", {}).get("login"),
            "created_at": pr_data.get("created_at"),
            "files_changed": pr_data.get("changed_files", 0),
            "additions": pr_data.get("additions", 0),
            "deletions": pr_data.get("deletions", 0),
        }


async def fetch_recent_activity(username: str, access_token: str, since: str | None = None) -> dict:
    """Fetch recent GitHub activity for a user."""
    if since is None:
        since_dt = datetime.now(timezone.utc) - timedelta(days=7)
        since = since_dt.isoformat()

    async with httpx.AsyncClient() as client:
        events_response = await client.get(
            f"{GITHUB_API_BASE}/users/{username}/events",
            headers=_headers(access_token),
            params={"per_page": 100},
        )
        events_response.raise_for_status()
        events = events_response.json()

        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        recent_events = [
            e for e in events
            if datetime.fromisoformat(e.get("created_at", "").replace("Z", "+00:00")) >= since_dt
        ]

        commits, prs_opened, prs_merged, issues_opened, reviews = 0, 0, 0, 0, 0
        repos_active = set()

        for event in recent_events:
            event_type = event.get("type", "")
            repos_active.add(event.get("repo", {}).get("name", ""))

            if event_type == "PushEvent":
                commits += event.get("payload", {}).get("size", 0)
            elif event_type == "PullRequestEvent":
                action = event.get("payload", {}).get("action", "")
                if action == "opened":
                    prs_opened += 1
                elif action == "closed" and event.get("payload", {}).get("pull_request", {}).get("merged"):
                    prs_merged += 1
            elif event_type == "IssuesEvent" and event.get("payload", {}).get("action") == "opened":
                issues_opened += 1
            elif event_type == "PullRequestReviewEvent":
                reviews += 1

        return {
            "period_start": since,
            "period_end": datetime.now(timezone.utc).isoformat(),
            "total_events": len(recent_events),
            "commits": commits,
            "prs_opened": prs_opened,
            "prs_merged": prs_merged,
            "issues_opened": issues_opened,
            "reviews": reviews,
            "repos_active": list(repos_active),
            "events": [
                {"type": e.get("type"), "repo": e.get("repo", {}).get("name"), "created_at": e.get("created_at")}
                for e in recent_events[:50]
            ],
        }


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Parse a GitHub PR URL into (owner, repo, pr_number)."""
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", url.strip())
    if not match:
        raise ValueError(f"Invalid GitHub PR URL: {url}")
    return match.group(1), match.group(2), int(match.group(3))
