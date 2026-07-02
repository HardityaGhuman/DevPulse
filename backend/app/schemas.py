"""
DevPulse — Pydantic Request/Response Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


# ── LLM Digest I/O (typed, provider-agnostic) ───────────────────

class WaitingPR(BaseModel):
    repo: str
    number: int
    title: str
    url: str
    age_days: int


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
    deltas: dict[str, int] = {}          # e.g. {"commits": 4, "prs_opened": -1}


class DigestResult(BaseModel):
    """The validated LLM output. Any provider must produce exactly this shape."""
    headline: str
    highlights: list[str]
    streak_comment: str
    top_repo: Optional[str] = None
    coaching_tip: str
    momentum: Literal["rising", "steady", "declining"]


# ── Digest Schemas ──────────────────────────────────────────────

class DigestSettingsRequest(BaseModel):
    digest_frequency: str = Field(..., pattern="^(off|daily|weekly)$")
    digest_day: Optional[str] = Field(
        "monday",
        pattern="^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$",
    )
    tracked_repos: Optional[list[str]] = None


class DigestSettingsResponse(BaseModel):
    digest_frequency: str
    digest_day: str
    tracked_repos: Optional[list[str]] = None


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
    digest_day: str
    tracked_repos: Optional[list[str]] = None
    created_at: str
