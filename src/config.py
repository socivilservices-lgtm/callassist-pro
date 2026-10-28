"""Application configuration loaded from environment variables / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime settings. Override via environment or a ``.env`` file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""
    admin_user_ids: str = ""  # comma separated Telegram IDs
    admin_api_key: str = ""

    database_url: str = "sqlite+aiosqlite:///./callassist.db"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 500
    openai_input_cost_per_1k: float = 0.00015
    openai_output_cost_per_1k: float = 0.0006

    elevenlabs_api_key: str = ""
    elevenlabs_default_voice: str = "21m00Tcm4TlvDq8ikWAM"
    aws_region: str = "us-east-1"
    polly_default_voice: str = "Joanna"

    stripe_api_key: str = "sk_test_mock"

    rate_limit_per_minute: int = Field(default=20, ge=1)
    log_level: str = "INFO"
    environment: str = "development"

    @property
    def admin_ids(self) -> set[int]:
        """Parsed set of admin Telegram user IDs."""
        return {int(x) for x in self.admin_user_ids.split(",") if x.strip().isdigit()}


@lru_cache
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()
