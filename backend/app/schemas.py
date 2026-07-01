"""
DevPulse — Pydantic Request/Response Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional


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
