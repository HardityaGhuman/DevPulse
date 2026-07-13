"""
DevPulse — Application Configuration
Reads all environment variables via Pydantic BaseSettings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM — LiteLLM reads these provider keys from the environment directly.
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Clerk
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""            # e.g. https://your-app.clerk.accounts.dev
    clerk_webhook_secret: str = ""    # Svix signing secret (whsec_...)

    # Cron (Cloud Scheduler shared secret)
    internal_cron_secret: str = ""

    # Email (Resend only)
    resend_api_key: str = ""
    email_from: str = "DevPulse <devpulse@localhost>"
    email_reply_to: str = ""

    # Frontend
    frontend_url: str = "http://localhost:5173"

    # Public URL of THIS API. Needed for the List-Unsubscribe one-click URL, which the mail
    # client fetches directly — it can't be a relative path or a frontend route. Unset => we
    # fall back to a dashboard link and skip the one-click header.
    api_base_url: str = ""
    unsubscribe_secret: str = ""      # falls back to internal_cron_secret when unset


settings = Settings()
