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

    # Gemini
    gemini_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # Clerk
    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    # Email
    email_provider: str = "resend"
    email_from: str = "DevPulse <devpulse@localhost>"
    email_reply_to: str = ""
    resend_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

    # GitHub OAuth
    github_client_id: str = ""
    github_client_secret: str = ""

    # Frontend
    frontend_url: str = "http://localhost:5173"


settings = Settings()
