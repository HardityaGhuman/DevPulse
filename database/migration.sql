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
