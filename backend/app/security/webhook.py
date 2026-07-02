"""Verify Clerk (Svix) webhook signatures before trusting the payload.

Clerk signs webhooks with Svix. Without this check, anyone could POST forged
user.created/updated events and create or overwrite user rows.
"""

from fastapi import HTTPException, status
from svix.webhooks import Webhook, WebhookVerificationError
from app.config import settings


def verify_svix(headers: dict, body: bytes) -> dict:
    """Return the verified payload dict, or raise HTTPException on failure."""
    if not settings.clerk_webhook_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook secret not configured")
    try:
        wh = Webhook(settings.clerk_webhook_secret)
        return wh.verify(body, {
            "svix-id": headers.get("svix-id", ""),
            "svix-timestamp": headers.get("svix-timestamp", ""),
            "svix-signature": headers.get("svix-signature", ""),
        })
    except WebhookVerificationError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook signature")
