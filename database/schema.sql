-- DevPulse Database Schema (fresh install)
-- Execute in Supabase Dashboard → SQL Editor → New Query → Paste → Run
--
-- Notes:
--  * GitHub access tokens are NOT stored — they are fetched live from Clerk per request.
--  * The backend uses the Supabase service key and bypasses RLS; RLS is enabled as a
--    backstop so that an exposed anon key grants no access (no anon policies are created).
--  * This file matches the LIVE prod schema as verified 2026-07-10 (scheduling columns +
--    period_key idempotency). Keep it in sync — the app CANNOT run against an older shape.

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clerk_id TEXT UNIQUE NOT NULL,
  email TEXT NOT NULL,
  github_username TEXT,
  digest_frequency TEXT DEFAULT 'off',   -- off | 6h | 12h | daily | weekly
  tracked_repos TEXT[],                  -- owner/name slugs; empty/NULL = whole account
  -- Scheduling anchor (all cadences fire relative to this local hour; see _is_due).
  digest_hour INT,                       -- 0–23 in digest_timezone; NULL → default 8
  digest_day TEXT,                       -- weekday for 'weekly' (monday…sunday); NULL → monday
  digest_timezone TEXT,                  -- IANA zone (e.g. Asia/Kolkata); NULL → UTC
  last_digest_at TIMESTAMPTZ,            -- when the last digest was sent (due-tracking)
  cached_digest JSONB,                   -- {result, context} cache (dashboard preview; now dead)
  cached_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE digests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  -- Stable identity for a digest window: interval-aware (a 6h digest gets 4/day, daily 1).
  -- Backs idempotent delivery (a Cloud Tasks retry finds the same key already sent → skips).
  period_key TEXT NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  activity_data JSONB NOT NULL,
  ai_summary TEXT NOT NULL,
  email_sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (user_id, period_key)
);

-- Indexes for common queries
CREATE INDEX idx_users_clerk_id ON users(clerk_id);
CREATE INDEX idx_digests_user_id ON digests(user_id);
CREATE INDEX idx_digests_period ON digests(period_start, period_end);

-- Row Level Security backstop (service role bypasses; no anon policies = anon has no access)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE digests ENABLE ROW LEVEL SECURITY;
