"""
DevPulse — Pydantic Request/Response Schemas
"""

import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from zoneinfo import ZoneInfo


# ── LLM Digest I/O (typed, provider-agnostic) ───────────────────

class WaitingPR(BaseModel):
    repo: str
    number: int
    title: str
    url: str
    age_days: int
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    is_draft: bool = False
    mergeable: str = "UNKNOWN"        # GraphQL enum: MERGEABLE | CONFLICTING | UNKNOWN
    reason: str = "yours"             # "review_requested" | "yours"


class ShippedPR(BaseModel):
    """A PR the user merged in the window — the "Shipped Today" section."""
    repo: str
    number: int
    title: str
    url: str


class WorkItem(BaseModel):
    """A grouped commit headline — the "Today's Work" log. Author's own words, not LLM prose."""
    repo: str
    headline: str
    commits: int = 1


class DigestContext(BaseModel):
    """The full, deterministic input handed to the LLM (PTCF 'Context')."""
    github_username: str
    period_start: str
    period_end: str
    commits: int
    prs_opened: int
    prs_merged: int
    issues_opened: int
    reviews: int
    repos_active: list[str]
    streak_days: int
    waiting_prs: list[WaitingPR] = []
    shipped_prs: list[ShippedPR] = []
    work_log: list[WorkItem] = []
    deltas: dict[str, int] = {}          # e.g. {"commits": 4, "prs_opened": -1}
    # Fixed trailing-7-day counts for the "Last 7 Days" stat strip — always a real week,
    # independent of the digest cadence (a 6h digest's own window would otherwise mislabel
    # tiny counts as weekly). Keys: prs_opened, prs_merged, reviews, issues_opened,
    # repos_active. Streak is NOT here — it stays streak_days (its own 365-day lookback).
    week_stats: dict[str, int] = {}


class DigestResult(BaseModel):
    """The validated LLM output. Any provider must produce exactly this shape."""
    headline: str
    momentum: Literal["rising", "steady", "declining"]

    # The headline is the ONLY LLM-authored text in the email (rides the preheader + AI Summary).
    # The prompt asks for <= 140 chars, but a model can ignore that — so hard-cap here rather than
    # trust it. We TRUNCATE (not reject) so a slightly-long headline still ships instead of failing
    # validation and dropping the whole digest to the facts-only fallback. Applies to every path
    # that builds a DigestResult (LLM parse + fallback). 160 = the 140 ask + a little slack.
    @field_validator("headline", mode="before")
    @classmethod
    def _bound_headline(cls, v):
        limit = 160
        s = " ".join(str(v).split())  # coerce + collapse whitespace/newlines
        return (s[: limit - 1].rstrip() + "…") if len(s) > limit else s


# ── Digest Schemas ──────────────────────────────────────────────

_DAYS = "^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$"


class DigestSettingsRequest(BaseModel):
    digest_frequency: str = Field(..., pattern="^(off|6h|12h|daily|weekly)$")
    # Bounded before storage: max 200 repos, each an owner/name slug (GitHub caps segments
    # at 39/100 chars; 141 covers owner + "/" + name with margin).
    tracked_repos: Optional[list[str]] = Field(None, max_length=200)
    # Scheduling for daily/weekly. hour = 0–23 in the user's tz; day = weekday for weekly.
    digest_hour: Optional[int] = Field(None, ge=0, le=23)
    digest_day: Optional[str] = Field(None, pattern=_DAYS)
    digest_timezone: Optional[str] = Field(None, max_length=64)

    @field_validator("tracked_repos")
    @classmethod
    def _valid_repos(cls, v):
        if v is None:
            return v
        for name in v:
            if not (0 < len(name) <= 141) or not re.fullmatch(r"[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+", name):
                raise ValueError("tracked_repos entries must be owner/name")
        return v

    @field_validator("digest_timezone")
    @classmethod
    def _valid_tz(cls, v):
        if v is None:
            return v
        try:
            ZoneInfo(v)
        except Exception as exc:
            raise ValueError("invalid IANA timezone") from exc
        return v


class DigestSettingsResponse(BaseModel):
    digest_frequency: str
    tracked_repos: Optional[list[str]] = None
    digest_hour: Optional[int] = None
    digest_day: Optional[str] = None
    digest_timezone: Optional[str] = None


class DigestHistoryItem(BaseModel):
    id: str
    period_start: str
    period_end: str
    ai_summary: str
    email_sent_at: Optional[str] = None
    created_at: str


# ── User Schemas ────────────────────────────────────────────────

class UserSyncRequest(BaseModel):
    """Clerk webhook payload (simplified)."""
    data: dict
    type: str


class UserProfile(BaseModel):
    id: str
    clerk_id: str
    email: str
    github_username: Optional[str] = None
    digest_frequency: str
    tracked_repos: Optional[list[str]] = None
    created_at: str
