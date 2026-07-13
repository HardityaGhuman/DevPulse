# DevPulse

[![CI](https://img.shields.io/github/actions/workflow/status/HardityaGhuman/DevPulse/ci.yml?style=for-the-badge&logo=github)](https://github.com/HardityaGhuman/DevPulse/actions)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)

**DevPulse** delivers a neatly formatted digest of your GitHub activity by email, on a cadence you pick. It aims to be a better progress tracker than GitHub's own notifications: accurate contribution counts, streaks, week-over-week momentum, and a nudge on the pull requests waiting on you. Every figure in the digest is rendered straight from GitHub data — the LLM writes only the one-line headline, so nothing is ever invented.

---

## The Problem It Solves

Keeping track of your own development progress is tedious, and GitHub's notifications are noisy. DevPulse aggregates your real GitHub activity for the period and emails you a clean, fact-driven digest: a one-line AI summary and momentum read, your activity stats with week-over-week deltas, your streak, the repos you touched, and — most usefully — the pull requests waiting on you.

## Key Features

- **Automated Developer Digests** — Opt into a cadence that suits you: `off / 6h / 12h / daily / weekly`, delivered at an hour (and weekday) you choose, in your own timezone. Facts are rendered directly (counts, deltas, streak, waiting PRs); the LLM adds only a one-line headline and a momentum read — no filler.
- **Opt-in by default** — a new account starts at `off`. DevPulse never emails anyone who didn't ask for it, and every digest carries a one-click unsubscribe.
- **Clean, email-safe template** — an editorial broadsheet built from tables and inline styles, locked to light so dark-mode clients can't invert it into a mess. Fluid to any width, so it holds up on a phone.
- **Accurate GitHub Activity** — Uses GitHub's GraphQL `contributionsCollection` API: commits, PRs, issues, reviews, active repos, and current streak — including private repositories.
- **PRs Waiting On You** — Surfaces open PRs you authored or that request your review, so nothing stalls.
- **Week-over-Week Momentum** — Compares against your previous digest for real deltas, not guesses.
- **GitHub OAuth via Clerk** — Sign in with GitHub. DevPulse reads your activity on your behalf; your GitHub token is never stored.

---

## How It Works

A React single-page app talks to a stateless FastAPI service over a JSON API.

### Architecture

```mermaid
flowchart TD
    subgraph Client
        SPA[React SPA]
    end
    
    subgraph GCP Cloud Run
        API[FastAPI Backend]
        TaskQueue[GCP Cloud Tasks]
    end
    
    subgraph External Services
        Clerk[Clerk Auth]
        GitHub[GitHub API]
        Supabase[(Supabase / PostgreSQL)]
        LLM[LiteLLM / Gemini]
        Resend[Resend Email]
        Cron[Cloud Scheduler]
    end

    SPA <--> API
    API <--> Clerk
    API <--> GitHub
    API <--> Supabase
    API <--> LLM
    API --> Resend
    
    Cron -->|"POST /internal/run-digests"| API
    API -->|"Enqueues"| TaskQueue
    TaskQueue -->|"POST /internal/digest/{id}"| API
```

1. **Authentication** — Sign in with GitHub through Clerk. The frontend attaches a Clerk-issued JWT to every request. The backend verifies the token against Clerk's JWKS, checks the issuer, and looks up (or auto-provisions) the user.
2. **GitHub access** — The backend fetches the user's GitHub OAuth token **live from Clerk** for each request and holds it in memory only — it is never persisted.
3. **Digest generation** — Activity is assembled into a typed context and passed to the LLM layer via **LiteLLM** (model-agnostic). The prompt follows the PTCF framework; output is validated against a strict schema.
4. **Persistence** — Digests are stored in PostgreSQL (Supabase), one row per period.
5. **Scheduled delivery** — an external cron (cron-job.org) calls a shared-secret-protected internal endpoint **at least hourly**. The backend selects the users who are due *at that hour in their own timezone*, fans them out through Cloud Tasks (one retryable task each, so one failure can't block the rest), and emails each digest via Resend. Delivery is idempotent per window: a retry after a successful send can't email anyone twice.

### Tech stack

**Frontend** — React + Vite, Tailwind CSS, React Router, Clerk for authentication.

**Backend** — FastAPI (Python 3.13), Supabase (PostgreSQL), LiteLLM (Gemini 2.5 Flash primary, Groq OpenAI gpt-oss-120b fallback), Resend for email. Deployed on Google Cloud Run.

### Security highlights

- **JWT auth via Clerk** — Signature (RS256/JWKS), exact issuer match, TTL-cached keys; generic errors. Fails **closed** if the issuer is unconfigured.
- **Signed webhooks** — The Clerk user-sync webhook requires a valid Svix signature.
- **No stored secrets** — GitHub tokens are fetched live from Clerk, never written to the DB.
- **Rate limiting** — Per-user limits on the LLM and email endpoints.
- **RLS backstop** — Row Level Security enabled; the backend uses the service role.
- **Capability-scoped unsubscribe** — `/api/unsubscribe/{token}` is the one unauthenticated route (mail clients POST it with no session). The URL carries an HMAC token; the only thing it can do is set that one user's cadence to `off`.

---

## Deployment (Google Cloud Run + Cloud Scheduler)

The backend is a stateless container; scheduling lives outside the app.

**1. Configure env** — copy `backend/.env.example` to `.env` and fill in every value.

**2. Deploy the API:**

```bash
cd backend
gcloud run deploy devpulse-api --source . --region <region> \
  --allow-unauthenticated --max-instances=2
```

Then set the environment variables (all keys from `.env.example`) in the Cloud Run Console
→ *Edit & deploy new revision → Variables & Secrets*. Doing it in the Console avoids shell
quoting issues with values that contain spaces (e.g. `EMAIL_FROM`). Env vars persist across
future `gcloud run deploy` runs.

**3. Schedule the digest cron** — create a job on [cron-job.org](https://cron-job.org) (or any
scheduler):
- URL: `<service-url>/internal/run-digests`
- Method: `POST`
- Header: `X-Internal-Secret: <INTERNAL_CRON_SECRET>`
- Schedule: **hourly** (`0 * * * *`)

The cron **must run at least hourly** — it is the clock for every cadence. Users pick a delivery
hour in their own timezone, and `run_all` only sends to those whose chosen hour is the current
one. A daily cron would strand every user who didn't pick that exact hour.

Any HTTP scheduler works — the endpoint just needs the secret header. (Google Cloud Scheduler
is a fine alternative if you prefer staying inside GCP.)

**4. Database** — run `database/schema.sql` on a fresh Supabase project, or `database/migration.sql` to upgrade an existing one.

The frontend deploys separately (e.g. Vercel) and points at the Cloud Run URL.

---

## Local Development

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env    # fill in values
uvicorn app.main:app --reload   # http://localhost:8000
pytest                          # run the test suite
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

The frontend reads the API base from `VITE_API_BASE_URL` (defaults to
`http://localhost:8000`). To point it at a deployed backend, set in `frontend/.env`:
```
VITE_API_BASE_URL=https://<your-cloud-run-service-url>
```
Auth tokens are Clerk session JWTs, attached automatically by `src/lib/api.js`.

## Project Layout

```
backend/          FastAPI service
  app/security/   Clerk JWT, Svix webhook, cron-secret, unsubscribe-token guards
  app/clients/    external APIs — Clerk, GitHub GraphQL
  app/services/   ai (LiteLLM), digest orchestration, Resend email
  app/routers/    users, digest, github, internal (cron), unsubscribe
database/         schema.sql (fresh) + migration.sql (upgrade)
frontend/         React + Vite SPA — landing + dashboard
```

## Status

**Live.** Backend on Cloud Run (GitHub Actions CD), frontend on Vercel. Sign in with GitHub, pick
a cadence, and the digest arrives by email.