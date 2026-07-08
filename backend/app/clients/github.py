"""
GitHub data client.

Uses the GraphQL `contributionsCollection` API for accurate activity counts and streaks
(includes private repos, unlike the REST events feed), plus REST search for "waiting" PRs
and a slim repo list for the frontend.
"""

import httpx
from datetime import datetime, timedelta, timezone

GRAPHQL = "https://api.github.com/graphql"
REST = "https://api.github.com"

# Streak spans a long trailing window, NOT the digest period — a daily digest's 24h window
# could only ever yield a 1-day streak. contributionsCollection allows up to ~1 year.
_STREAK_WINDOW_DAYS = 365

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
        contributions { totalCount }
      }
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


_STREAK_QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
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


_COUNT_QUERY = """
query($q:String!) { search(query:$q, type:ISSUE) { issueCount } }
"""


def _repo_filter(repos: list[str] | None) -> str:
    """GitHub search `repo:` qualifiers scoping a query to tracked repos (empty = whole account).
    Repo slugs are validated owner/name on write (schemas.py), so they're safe to interpolate."""
    return " ".join(f"repo:{r}" for r in (repos or []))


async def _search_count(client: httpx.AsyncClient, token: str, q: str) -> int:
    """Exact match count for a search query (issueCount, not the capped node list)."""
    r = await client.post(GRAPHQL, headers=_headers(token),
                          json={"query": _COUNT_QUERY, "variables": {"q": q}})
    if r.status_code != 200:
        return 0
    return ((r.json().get("data", {}).get("search", {}) or {}).get("issueCount", 0)) or 0


def _current_streak(weeks: list[dict]) -> int:
    """Consecutive most-recent days with any contribution.

    Two edge cases matter: (1) GitHub pads the current week with zero-count *future* days —
    drop them or they'd read as a broken streak. (2) A still-empty *today* must not break a
    streak that ran through yesterday (you may not have pushed yet) — skip it, don't stop.
    """
    today = datetime.now(timezone.utc).date()
    days = [d for w in weeks for d in w.get("contributionDays", [])
            if datetime.fromisoformat(d["date"]).date() <= today]
    days.sort(key=lambda d: d["date"], reverse=True)
    streak = 0
    for i, d in enumerate(days):
        if d.get("contributionCount", 0) > 0:
            streak += 1
        elif i == 0 and datetime.fromisoformat(d["date"]).date() == today:
            continue                       # empty today: skip, don't break yesterday's run
        else:
            break
    return streak


async def fetch_contributions(username: str, token: str, since: str, until: str,
                              tracked: list[str] | None = None) -> dict:
    """Fetch accurate contribution counts + streak for the period.

    If `tracked` is given, top-line counts are scoped to those repos: commits from the
    per-repo commit breakdown, and opened-PR / issue / review counts from repo-filtered
    search (exact issueCount). Streak stays account-wide — a per-repo streak isn't meaningful.
    """
    # Streak needs a wider lookback than the digest window; clamp `from` to <= now.
    streak_from = (datetime.now(timezone.utc) - timedelta(days=_STREAK_WINDOW_DAYS)).isoformat()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            GRAPHQL,
            headers=_headers(token),
            json={"query": _CONTRIB_QUERY,
                  "variables": {"login": username, "from": since, "to": until}},
        )
        r.raise_for_status()
        body = r.json()
        # GraphQL returns HTTP 200 even on query errors or a null user (bad login, missing
        # token scope). Left unchecked, `user` is None -> every count defaults to 0 and we'd
        # email an honest-looking "quiet day" that's actually a broken fetch. Fail loudly so
        # the caller skips/retries this user instead of sending a misleading zero digest.
        if body.get("errors"):
            raise RuntimeError(f"GitHub GraphQL error for {username}: {body['errors']}")
        gh_user = (body.get("data") or {}).get("user")
        if gh_user is None:
            raise RuntimeError(f"GitHub returned no user for '{username}' (bad login or token scope)")
        cc = gh_user.get("contributionsCollection", {})

        sr = await client.post(
            GRAPHQL,
            headers=_headers(token),
            json={"query": _STREAK_QUERY,
                  "variables": {"login": username, "from": streak_from, "to": until}},
        )
        streak_cc = ((sr.json().get("data", {}).get("user", {}) or {})
                     .get("contributionsCollection", {}) if sr.status_code == 200 else {})

        by_repo = cc.get("commitContributionsByRepository", [])
        weeks = streak_cc.get("contributionCalendar", {}).get("weeks", [])

        if tracked:
            tset = set(tracked)
            rf = _repo_filter(tracked)
            repos = [x["repository"]["nameWithOwner"] for x in by_repo
                     if x["repository"]["nameWithOwner"] in tset]
            commits = sum(x.get("contributions", {}).get("totalCount", 0)
                          for x in by_repo if x["repository"]["nameWithOwner"] in tset)
            prs = await _search_count(
                client, token, f"is:pr author:{username} created:>={since} archived:false {rf}")
            issues = await _search_count(
                client, token, f"is:issue author:{username} created:>={since} archived:false {rf}")
            # GitHub search has no "reviewed-on" date qualifier; approximate the window with
            # `updated:` — close enough for the secondary reviews stat.
            reviews = await _search_count(
                client, token, f"is:pr reviewed-by:{username} updated:>={since} archived:false {rf}")
        else:
            repos = [x["repository"]["nameWithOwner"] for x in by_repo]
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


_WAITING_QUERY = """
query($q:String!) {
  search(query:$q, type:ISSUE, first:20) {
    nodes {
      ... on PullRequest {
        number title url createdAt isDraft mergeable
        additions deletions changedFiles
        repository { nameWithOwner }
      }
    }
  }
}
"""


async def _search_prs(client: httpx.AsyncClient, token: str, q: str, reason: str) -> list[dict]:
    r = await client.post(GRAPHQL, headers=_headers(token),
                          json={"query": _WAITING_QUERY, "variables": {"q": q}})
    if r.status_code != 200:
        return []
    nodes = (r.json().get("data", {}).get("search", {}) or {}).get("nodes", []) or []
    out = []
    for n in nodes:
        if not n:                      # non-PR nodes come back as {}
            continue
        created = parse_iso(n["createdAt"])
        out.append({
            "repo": n["repository"]["nameWithOwner"],
            "number": n["number"], "title": n["title"], "url": n["url"],
            "age_days": (datetime.now(timezone.utc) - created).days,
            "additions": n.get("additions", 0), "deletions": n.get("deletions", 0),
            "changed_files": n.get("changedFiles", 0),
            "is_draft": n.get("isDraft", False),
            "mergeable": n.get("mergeable", "UNKNOWN"),
            "reason": reason,
        })
    return out


async def fetch_waiting_prs(username: str, token: str, tracked: list[str] | None = None) -> list[dict]:
    """Open PRs requesting the user's review OR authored by them. Review-requested first.
    Scoped to `tracked` repos when set."""
    rf = _repo_filter(tracked)
    async with httpx.AsyncClient(timeout=20) as client:
        review = await _search_prs(
            client, token, f"is:open is:pr review-requested:{username} archived:false {rf}".strip(),
            "review_requested")
        authored = await _search_prs(
            client, token, f"is:open is:pr author:{username} archived:false {rf}".strip(), "yours")
    seen, merged = set(), []
    for pr in review + authored:       # review-requested takes priority on dupes
        if pr["url"] in seen:
            continue
        seen.add(pr["url"])
        merged.append(pr)
    merged.sort(key=lambda p: p["age_days"], reverse=True)
    return merged


_MERGED_QUERY = """
query($q:String!) {
  search(query:$q, type:ISSUE, first:20) {
    issueCount
    nodes {
      ... on PullRequest {
        number title url mergedAt
        repository { nameWithOwner }
      }
    }
  }
}
"""


async def fetch_merged_prs(username: str, token: str, since: str,
                           tracked: list[str] | None = None) -> dict:
    """PRs the user merged in the window — feeds "Shipped Today". Returns an honest count
    (`issueCount`, not the capped node list) plus title/repo/url for each. Scoped to
    `tracked` repos when set."""
    # Full ISO timestamp (not date-only) so a 6h/12h digest counts its actual interval, not
    # the whole UTC day. GitHub search accepts `>=YYYY-MM-DDTHH:MM:SS+00:00`.
    q = f"is:pr is:merged author:{username} merged:>={since} archived:false {_repo_filter(tracked)}".strip()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(GRAPHQL, headers=_headers(token),
                              json={"query": _MERGED_QUERY, "variables": {"q": q}})
        if r.status_code != 200:
            return {"count": 0, "prs": []}
        search = (r.json().get("data", {}).get("search", {}) or {})
    prs = [{
        "repo": n["repository"]["nameWithOwner"], "number": n["number"],
        "title": n["title"], "url": n["url"],
    } for n in (search.get("nodes") or []) if n]
    return {"count": search.get("issueCount", len(prs)), "prs": prs}


async def fetch_work_log(username: str, token: str, since: str,
                         tracked: list[str] | None = None) -> list[dict]:
    """Human-readable work log from commit headlines in the window — feeds "Today's Work".
    First line of each commit message only (no body); grouped by (repo, headline) with a
    count. Never AI-interpreted — the commit author's own words, verbatim. Scoped to
    `tracked` repos when set."""
    # Full ISO timestamp (see fetch_merged_prs) so sub-daily windows aren't widened to a day.
    q = f"author:{username} committer-date:>={since} {_repo_filter(tracked)}".strip()
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{REST}/search/commits", headers=_headers(token),
                             params={"q": q, "sort": "committer-date",
                                     "order": "desc", "per_page": 50})
        if r.status_code != 200:
            return []
        items = r.json().get("items", []) or []
    grouped: dict[tuple[str, str], dict] = {}     # (repo, headline) -> {repo, headline, commits}
    for it in items:
        headline = (it.get("commit", {}).get("message") or "").split("\n", 1)[0].strip()
        if not headline:
            continue
        repo = it.get("repository", {}).get("full_name", "")
        key = (repo, headline)
        if key in grouped:
            grouped[key]["commits"] += 1
        else:
            grouped[key] = {"repo": repo, "headline": headline, "commits": 1}
    return list(grouped.values())


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
