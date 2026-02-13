"""Tests for config secret validation."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings


class TestSecretValidation:
    """Test that required secrets are validated at startup."""

    def test_missing_single_secret_raises_error(self):
        """Missing one required secret raises ValueError."""
        env = {
            "SUPABASE_URL": "",  # Missing
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "test-livekit-key",
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
        }
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            assert "SUPABASE_URL" in str(exc_info.value)

    def test_missing_multiple_secrets_lists_all(self):
        """Missing multiple secrets lists all in error message."""
        env = {
            "SUPABASE_URL": "",  # Missing
            "SUPABASE_ANON_KEY": "",  # Missing
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "",  # Missing
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
        }
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)

            error_str = str(exc_info.value)
            assert "SUPABASE_URL" in error_str
            assert "SUPABASE_ANON_KEY" in error_str
            assert "LIVEKIT_API_KEY" in error_str

    def test_all_secrets_present_succeeds(self):
        """All required secrets present allows Settings to load."""
        env = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "test-livekit-key",
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
        }
        with patch.dict("os.environ", env, clear=True):
            settings = Settings(_env_file=None)
            assert settings.supabase_url == "https://test.supabase.co"

    def test_jwt_secret_is_optional(self):
        """jwt_secret is optional (not required for Supabase JWKS auth)."""
        env = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "test-livekit-key",
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
            # JWT_SECRET intentionally not set
        }
        with patch.dict("os.environ", env, clear=True):
            settings = Settings(_env_file=None)
            assert settings.jwt_secret == ""  # Default empty is OK


class TestEnvironmentSetting:
    """Test environment setting validation."""

    def test_environment_defaults_to_development(self):
        """Environment defaults to development when not set."""
        env = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "test-livekit-key",
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
        }
        with patch.dict("os.environ", env, clear=True):
            settings = Settings(_env_file=None)
            assert settings.environment == "development"

    def test_environment_can_be_set_to_production(self):
        """Environment can be explicitly set to production."""
        env = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "test-livekit-key",
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
            "ENVIRONMENT": "production",
        }
        with patch.dict("os.environ", env, clear=True):
            settings = Settings(_env_file=None)
            assert settings.environment == "production"

    def test_environment_can_be_set_to_staging(self):
        """Environment can be set to staging."""
        env = {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_ANON_KEY": "test-anon-key",
            "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
            "LIVEKIT_API_KEY": "test-livekit-key",
            "LIVEKIT_API_SECRET": "test-livekit-secret",
            "LIVEKIT_URL": "wss://test.livekit.cloud",
            "ENVIRONMENT": "staging",
        }
        with patch.dict("os.environ", env, clear=True):
            settings = Settings(_env_file=None)
            assert settings.environment == "staging"
