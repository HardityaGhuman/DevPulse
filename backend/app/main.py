"""
DevPulse — FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import github, digest, users
# from app.routers import internal  # enabled in Task 8
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devpulse")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("DevPulse starting up...")
    start_scheduler()
    yield
    logger.info("DevPulse shutting down...")
    stop_scheduler()


app = FastAPI(
    title="DevPulse API",
    description="AI-powered GitHub intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
)

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
# app.include_router(internal.router)  # enabled in Task 8


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {"status": "healthy", "service": "devpulse-api"}
