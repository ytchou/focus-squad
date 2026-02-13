from functools import lru_cache
from typing import ClassVar

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Required secrets (validated at startup)
    REQUIRED_SECRETS: ClassVar[list[str]] = [
        "supabase_url",
        "supabase_anon_key",
        "supabase_service_role_key",
        "livekit_api_key",
        "livekit_api_secret",
        "livekit_url",
    ]

    # App
    app_name: str = "Focus Squad API"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379"

    # LiveKit
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_url: str = ""

    # JWT (optional - not used with Supabase JWKS auth)
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"

    # Rate limiting
    rate_limit_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        """Validate that all required secrets are set (non-empty)."""
        missing = []
        for secret_name in self.REQUIRED_SECRETS:
            value = getattr(self, secret_name, "")
            if not value or not value.strip():
                # Convert to uppercase env var name for error message
                env_name = secret_name.upper()
                missing.append(env_name)

        if missing:
            raise ValueError(
                f"Missing required secrets: {', '.join(missing)}. "
                "Set these environment variables before starting the application."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
