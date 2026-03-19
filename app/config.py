from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql://localhost:5432/blackkeyx"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    aws_s3_bucket: str = "blackkeyx-documents"

    # OpenAI
    openai_api_key: str = ""

    # LiveKit
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_sip_trunk_id: str = ""
    livekit_sip_number: str = ""  # Outbound caller ID (E.164 format)

    # Admin Authentication
    admin_password: str = "changeme"
    admin_api_key: str = "changeme-api-key"

    # Agent Callback Authentication (shared secret with voice agent)
    agent_callback_secret: str = "changeme-agent-secret"

    # Rate Limiting (slowapi format: "N/period")
    rate_limit_lead: str = "5/minute"
    rate_limit_admin_auth: str = "5/minute"
    rate_limit_global: str = "100/minute"

    # Callback Scheduler
    callback_scheduler_enabled: bool = True
    callback_poll_interval_seconds: int = 30
    callback_grace_window_minutes: int = 2
    callback_max_retries: int = 3

    # Voicemail Detection
    voicemail_detection_enabled: bool = True
    voicemail_max_retries: int = 1
    voicemail_retry_delay_days: int = 3

    # Investor Portal — Google OAuth + JWT
    google_client_id: str = ""
    jwt_secret_key: str = "changeme-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # Investor Portal — Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_pro_price_id: str = ""
    free_plan_deal_limit: int = 3

    # Application
    debug: bool = False
    cors_origins: List[str] = ["http://localhost:3000"]

    @property
    def async_database_url(self) -> str:
        """Convert database URL to async version for asyncpg."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
