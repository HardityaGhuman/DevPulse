"""
DevPulse — FastAPI Application Entry Point

Scheduling runs externally (Google Cloud Scheduler -> POST /internal/run-digests), so the
app carries no in-process scheduler — it stays stateless and Cloud Run can scale to zero.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.rate_limit import limiter
from app.routers import github, digest, users, internal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devpulse")

app = FastAPI(
    title="DevPulse API",
    description="Developer activity digests delivered by email",
    version="2.0.0",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

local_frontend_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys([settings.frontend_url, *local_frontend_origins])),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(github.router)
app.include_router(digest.router)
app.include_router(users.router)
app.include_router(internal.router)


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {"status": "healthy", "service": "devpulse-api"}
