-- DevPulse — Migration for an EXISTING instance (pre-refactor -> v2)
-- Execute in Supabase Dashboard → SQL Editor. Review each step.

-- 1. Stop storing GitHub tokens (now fetched live from Clerk).
ALTER TABLE users DROP COLUMN IF EXISTS github_access_token;

-- 2. Drop the removed review feature.
DROP TABLE IF EXISTS reviews;

-- 3. One digest per (user, period_end). If duplicates exist, dedupe first:
--    DELETE FROM digests d USING digests d2
--    WHERE d.user_id = d2.user_id AND d.period_end = d2.period_end AND d.ctid < d2.ctid;
ALTER TABLE digests
  ADD CONSTRAINT digests_user_period_unique UNIQUE (user_id, period_end);

-- 4. Enable RLS backstop (backend service role bypasses it).
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE digests ENABLE ROW LEVEL SECURITY;

-- ── Interval frequencies (v3) ────────────────────────────────────
ALTER TABLE users ALTER COLUMN digest_frequency SET DEFAULT 'off';
ALTER TABLE users DROP COLUMN IF EXISTS digest_day;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_digest_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS cached_digest JSONB;
ALTER TABLE users ADD COLUMN IF NOT EXISTS cached_at TIMESTAMPTZ;
UPDATE users SET digest_frequency='off'
  WHERE digest_frequency NOT IN ('off','6h','12h','daily','weekly');

-- ── Custom delivery anchor + interval-aware idempotency (v4, 2026-07-10) ──────────
-- These columns/constraint were applied by hand in prod but were missing from this file
-- (the code depends on them). Re-adds `digest_day` (dropped above) for weekly scheduling.
ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_hour INT;         -- 0–23 local; NULL → 8
ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_day TEXT;         -- weekly weekday; NULL → monday
ALTER TABLE users ADD COLUMN IF NOT EXISTS digest_timezone TEXT;    -- IANA zone; NULL → UTC

-- Move digest idempotency from (user_id, period_end) to interval-aware (user_id, period_key).
-- 1) add the column, 2) backfill existing rows (date-based key for the old daily cadence),
-- 3) swap the unique constraint.
ALTER TABLE digests ADD COLUMN IF NOT EXISTS period_key TEXT;
UPDATE digests SET period_key = 'daily:' || period_end::text WHERE period_key IS NULL;
ALTER TABLE digests ALTER COLUMN period_key SET NOT NULL;
ALTER TABLE digests DROP CONSTRAINT IF EXISTS digests_user_period_unique;
ALTER TABLE digests DROP CONSTRAINT IF EXISTS digests_user_id_period_end_key;
ALTER TABLE digests ADD CONSTRAINT digests_user_id_period_key_key UNIQUE (user_id, period_key);
