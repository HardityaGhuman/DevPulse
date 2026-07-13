"""
DevPulse — FastAPI Application Entry Point

Scheduling runs externally (Google Cloud Scheduler -> POST /internal/run-digests), so the
app carries no in-process scheduler — it stays stateless and Cloud Run can scale to zero.
"""

import os
import logging
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.rate_limit import limiter
from app.routers import github, digest, users, internal, unsubscribe

logging.basicConfig(level=logging.INFO)
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        # %-style args (logger.error("x %s", y)) need this to interpolate; without it the
        # event stays literal and args dump as a raw positional_args list.
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        # Render exc_info into a real traceback string; without it exc_info=True is just `true`.
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("devpulse")

app = FastAPI(
    title="DevPulse API",
    description="Developer activity digests delivered by email",
    version="2.0.0",
)

# Prometheus metrics. Always instrument; only expose the public /metrics endpoint when
# explicitly enabled — it leaks route names + traffic/latency timing, so it stays off in the
# public prod deploy unless a private scraper needs it (EXPOSE_METRICS=true).
_instrumentator = Instrumentator().instrument(app)
if os.environ.get("EXPOSE_METRICS", "false").lower() == "true":
    _instrumentator.expose(app)

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
app.include_router(unsubscribe.router)


@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {"status": "healthy", "service": "devpulse-api"}
