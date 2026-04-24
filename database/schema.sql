-- DevPulse Database Schema
-- Execute this in Supabase Dashboard → SQL Editor → New Query → Paste → Run

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clerk_id TEXT UNIQUE NOT NULL,
  email TEXT NOT NULL,
  github_username TEXT,
  github_access_token TEXT,
  digest_frequency TEXT DEFAULT 'daily',
  digest_day TEXT DEFAULT 'monday',
  tracked_repos TEXT[],
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  input_content TEXT,
  language TEXT,
  pr_url TEXT,
  pr_number INT,
  repo_name TEXT,
  review_result JSONB NOT NULL,
  share_token TEXT UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE digests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  activity_data JSONB NOT NULL,
  ai_summary TEXT NOT NULL,
  email_sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX idx_users_clerk_id ON users(clerk_id);
CREATE INDEX idx_reviews_user_id ON reviews(user_id);
CREATE INDEX idx_reviews_share_token ON reviews(share_token);
CREATE INDEX idx_digests_user_id ON digests(user_id);
CREATE INDEX idx_digests_period ON digests(period_start, period_end);
