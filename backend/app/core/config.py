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

    # Environment (development, staging, production)
    environment: str = "development"

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

    @model_validator(mode="after")
    def validate_cors_origins_in_production(self) -> "Settings":
        """Validate CORS origins are safe in production."""
        from urllib.parse import urlparse

        if self.environment != "production":
            return self

        unsafe_hostnames = {"localhost", "127.0.0.1", "0.0.0.0"}

        for origin in self.cors_origins:
            # Check for wildcard
            if origin == "*":
                raise ValueError(
                    "Wildcard (*) CORS origin is not allowed in production. "
                    "Specify exact origins instead."
                )

            # Parse URL and check hostname exactly (not substring)
            try:
                parsed = urlparse(origin)
                hostname = parsed.hostname or ""
            except Exception:
                hostname = origin  # Fall back to raw string if parsing fails

            # Check for exact unsafe hostname matches
            if hostname in unsafe_hostnames:
                raise ValueError(
                    f"CORS origin '{origin}' uses hostname '{hostname}' which is not "
                    f"allowed in production. Use HTTPS production URLs instead."
                )

        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
