# DevPulse

[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)

**DevPulse** delivers a neatly formatted digest of your GitHub activity by email — daily or weekly — written by an AI coach. It aims to be a better progress tracker than GitHub's own notifications: accurate contribution counts, streaks, week-over-week momentum, and a nudge on the pull requests waiting on you.

---

## The Problem It Solves

Keeping track of your own development progress is tedious, and GitHub's notifications are noisy. DevPulse aggregates your real GitHub activity for the period, has an LLM turn it into a punchy summary — headline, highlights, streak, momentum, and one actionable tip — and emails it to you on the schedule you choose.

## Key Features

- **Automated Developer Digests** — Opt into daily or weekly email summaries. An AI coach turns raw activity into a headline, highlights, a momentum read, and an actionable tip.
- **Accurate GitHub Activity** — Uses GitHub's GraphQL `contributionsCollection` API: commits, PRs, issues, reviews, active repos, and current streak — including private repositories.
- **PRs Waiting On You** — Surfaces open PRs you authored or that request your review, so nothing stalls.
- **Week-over-Week Momentum** — Compares against your previous digest for real deltas, not guesses.
- **GitHub OAuth via Clerk** — Sign in with GitHub. DevPulse reads your activity on your behalf; your GitHub token is never stored.

---

## How It Works

A React single-page app talks to a stateless FastAPI service over a JSON API.

1. **Authentication** — Sign in with GitHub through Clerk. The frontend attaches a Clerk-issued JWT to every request. The backend verifies the token against Clerk's JWKS, checks the issuer, and looks up (or auto-provisions) the user.
2. **GitHub access** — The backend fetches the user's GitHub OAuth token **live from Clerk** for each request and holds it in memory only — it is never persisted.
3. **Digest generation** — Activity is assembled into a typed context and passed to the LLM layer via **LiteLLM** (model-agnostic). The prompt follows the PTCF framework; output is validated against a strict schema.
4. **Persistence** — Digests are stored in PostgreSQL (Supabase), one row per period.
5. **Scheduled delivery** — Google Cloud Scheduler calls a shared-secret-protected internal endpoint on a cron. The backend selects due users (daily every day, weekly on their chosen day), generates each digest, and emails it via Resend.

### Tech stack

**Frontend** — React + Vite, Tailwind CSS, React Router, Clerk for authentication.

**Backend** — FastAPI (Python 3.13), Supabase (PostgreSQL), LiteLLM (Gemini 2.5 Flash primary, Groq Llama-3.3-70B fallback), Resend for email. Deployed on Google Cloud Run.

### Security highlights

- **JWT auth via Clerk** — Signature (RS256/JWKS), issuer, and TTL-cached keys; generic errors.
- **Signed webhooks** — The Clerk user-sync webhook requires a valid Svix signature.
- **No stored secrets** — GitHub tokens are fetched live from Clerk, never written to the DB.
- **Rate limiting** — Per-user limits on the LLM and email endpoints.
- **RLS backstop** — Row Level Security enabled; the backend uses the service role.

---

## Deployment (Google Cloud Run + Cloud Scheduler)

The backend is a stateless container; scheduling lives outside the app.

**1. Configure env** — copy `backend/.env.example` to `.env` and fill in every value.

**2. Deploy the API:**

```bash
cd backend
gcloud run deploy devpulse-api \
  --source . \
  --region <region> \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=...,GROQ_API_KEY=...,SUPABASE_URL=...,SUPABASE_SERVICE_KEY=...,CLERK_SECRET_KEY=...,CLERK_JWKS_URL=...,CLERK_ISSUER=...,CLERK_WEBHOOK_SECRET=...,INTERNAL_CRON_SECRET=...,RESEND_API_KEY=...,EMAIL_FROM=...,FRONTEND_URL=..."
```

**3. Schedule the digest cron:**

```bash
gcloud scheduler jobs create http devpulse-digest \
  --schedule "0 8 * * *" \
  --uri "<service-url>/internal/run-digests" \
  --http-method POST \
  --headers "X-Internal-Secret=<INTERNAL_CRON_SECRET>"
```

**4. Database** — run `database/schema.sql` on a fresh Supabase project, or `database/migration.sql` to upgrade an existing one.

The frontend deploys separately (e.g. Vercel) and points at the Cloud Run URL.
