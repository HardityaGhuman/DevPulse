# DevPulse

AI-powered GitHub intelligence platform. Get instant code reviews, PR analysis, and automated developer activity digests — all powered by Google Gemini.

## Architecture

```
Frontend:  React + Vite + TailwindCSS + shadcn/ui → Vercel
Backend:   FastAPI (Python) → Render
Auth:      Clerk (GitHub OAuth)
Database:  Supabase (PostgreSQL)
LLM:       Google Gemini API (gemini-2.5-flash)
Email:     Resend SDK
Scheduler: APScheduler
```

## Quick Start

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Fill in your keys
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env  # Fill in your keys
npm run dev
```

### Database

1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Paste the contents of `database/schema.sql`
4. Click Run

## Environment Variables

See `backend/.env.example` and `frontend/.env.example` for all required keys.
