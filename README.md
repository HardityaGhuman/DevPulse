# DevPulse

DevPulse is an AI-powered developer intelligence platform for GitHub workflows. It provides instant code reviews, pull request analysis, review sharing, GitHub activity tracking, and automated developer digests powered by Google Gemini.

## Features

- AI code reviews for pasted snippets with bug, security, complexity, and best-practice feedback
- GitHub pull request reviews from a PR URL, including risk level and merge recommendation
- Review history with shareable public review links
- GitHub repository and activity views for authenticated users
- Daily or weekly AI-generated developer digests
- Email delivery for digests through SMTP or Resend
- Clerk authentication with GitHub OAuth
- Supabase-backed persistence for users, reviews, and digest history

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, Tailwind CSS, Clerk, Framer Motion, Lucide |
| Backend | FastAPI, Uvicorn, Pydantic Settings |
| Database | Supabase PostgreSQL |
| Auth | Clerk with GitHub OAuth |
| AI | Google Gemini 2.5 Flash |
| Email | SMTP or Resend |
| Scheduler | APScheduler |

## Project Structure

```text
DevPulse/
├── backend/
│   ├── app/
│   │   ├── routers/       # FastAPI route modules
│   │   ├── services/      # Gemini, GitHub, email, digest logic
│   │   ├── middleware/    # Clerk JWT authentication
│   │   ├── main.py        # FastAPI app entry point
│   │   └── scheduler.py   # Scheduled digest job
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/         # App routes and screens
│   │   ├── components/    # Shared UI components
│   │   └── lib/           # API client and utilities
│   └── package.json
├── database/
│   └── schema.sql         # Supabase schema
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 20+
- npm
- Supabase project
- Clerk application with GitHub OAuth enabled
- Google Gemini API key
- Resend API key

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd DevPulse
```

### 2. Set up the database

1. Open your Supabase project dashboard.
2. Go to **SQL Editor**.
3. Paste the contents of `database/schema.sql`.
4. Run the query.

This creates the `users`, `reviews`, and `digests` tables plus indexes for common lookups.

### 3. Configure the backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `backend/.env`:

```env
GEMINI_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
CLERK_SECRET_KEY=
CLERK_JWKS_URL=
RESEND_API_KEY=
EMAIL_PROVIDER=smtp
EMAIL_FROM="DevPulse <your-email@example.com>"
EMAIL_REPLY_TO=
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_TLS=true
SMTP_USE_SSL=false
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
FRONTEND_URL=http://localhost:5173
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

The backend health check is available at:

```text
http://localhost:8000/health
```

### 4. Configure the frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
```

Fill in `frontend/.env`:

```env
VITE_CLERK_PUBLISHABLE_KEY=
VITE_API_BASE_URL=http://localhost:8000
```

Start the frontend:

```bash
npm run dev
```

The app runs at:

```text
http://localhost:5173
```

## API Overview

### Review

- `POST /api/review/code` - review pasted source code
- `POST /api/review/pr` - review a GitHub pull request
- `GET /api/review/history` - fetch authenticated user's review history
- `GET /api/review/{review_id}` - fetch one authenticated user's review
- `GET /api/review/share/{token}` - fetch a public shared review

### GitHub

- `GET /api/github/repos` - fetch authenticated user's GitHub repositories
- `GET /api/github/activity?days=7` - fetch recent GitHub activity

### Digest

- `GET /api/digest/settings` - fetch digest preferences
- `POST /api/digest/settings` - update digest preferences
- `GET /api/digest/history` - fetch digest history
- `POST /api/digest/preview` - generate a digest preview
- `POST /api/digest/send-now` - generate and email a digest immediately

### Users

- `POST /api/users/sync` - sync Clerk user webhook data
- `GET /api/users/me` - fetch the current user profile

## Authentication Notes

DevPulse uses Clerk JWTs on protected API routes. The frontend injects the active Clerk token into API requests, and the backend verifies tokens through Clerk's JWKS endpoint.

For GitHub-powered features, enable GitHub OAuth in Clerk. The backend can retrieve the user's GitHub OAuth token from Clerk and store it in Supabase for repository, activity, and PR review workflows.

## Scheduled Digests

The backend starts an APScheduler job on application startup. The job runs every day at `08:00 UTC`, finds users with digests enabled, generates a Gemini-powered activity summary, stores it in Supabase, and sends it through the configured email provider.

Users can choose:

- `daily`
- `weekly`
- `off`

Weekly digests use the configured `digest_day`.

## Useful Scripts

### Frontend

```bash
npm run dev       # Start Vite dev server
npm run build     # Build production assets
npm run preview   # Preview production build
npm run lint      # Run ESLint
```

### Backend

```bash
uvicorn app.main:app --reload --port 8000
```

## Deployment

The project is structured for a split deployment:

- Frontend on Vercel or another static frontend host
- Backend on Render, Fly.io, Railway, or another Python web service host
- Database on Supabase

For production, set `FRONTEND_URL` on the backend to your deployed frontend origin and set `VITE_API_BASE_URL` on the frontend to your deployed API URL.

## License

No license has been added yet. Add one before publishing if you want to define how others can use this project.
