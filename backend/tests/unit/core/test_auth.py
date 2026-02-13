"""Unit tests for auth module (app/core/auth.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.auth import (
    AuthOptionalUser,
    AuthUser,
    decode_supabase_token,
    get_current_user,
    get_jwks,
    get_optional_user,
    get_signing_key,
    get_user_from_state,
    require_auth_from_state,
)


class TestGetJwks:
    """Tests for get_jwks() function (now async)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fetches_jwks_from_supabase(self, test_jwks) -> None:
        """Successfully fetches JWKS from Supabase endpoint."""
        from app.core.auth import _jwks_cache

        # Mock the _fetch_keys method on the global cache
        with patch.object(_jwks_cache, "_fetch_keys", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = test_jwks

            result = await get_jwks()

            assert result == test_jwks
            assert "keys" in result
            mock_fetch.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_cached_jwks_on_subsequent_calls(self, test_jwks) -> None:
        """Returns cached JWKS without making additional HTTP requests."""
        from app.core.auth import _jwks_cache

        with patch.object(_jwks_cache, "_fetch_keys", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = test_jwks

            # First call - should fetch
            result1 = await get_jwks()
            # Second call - should use cache
            result2 = await get_jwks()

            assert result1 == result2
            mock_fetch.assert_called_once()  # Only one HTTP call

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_503_on_http_error(self) -> None:
        """Raises 503 when JWKS fetch fails."""
        from app.core.auth import _jwks_cache

        with patch.object(_jwks_cache, "_fetch_keys", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = HTTPException(
                status_code=503, detail="Failed to fetch JWKS: Connection failed"
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_jwks()

            assert exc_info.value.status_code == 503
            assert "Failed to fetch JWKS" in exc_info.value.detail


class TestGetSigningKey:
    """Tests for get_signing_key() function (now async)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_matching_key_by_kid(
        self, valid_jwt_token, test_jwks, jwks_key_id
    ) -> None:
        """Returns the key matching the token's kid."""
        with patch("app.core.auth.get_jwks", new_callable=AsyncMock) as mock_get_jwks:
            mock_get_jwks.return_value = test_jwks

            result = await get_signing_key(valid_jwt_token)

            assert result["kid"] == jwks_key_id
            assert result["kty"] == "RSA"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_first_key_when_no_kid_match(
        self, test_jwks, rsa_private_key_pem
    ) -> None:
        """Falls back to first key when no kid matches."""
        from jose import jwt

        # Create token with different kid
        token = jwt.encode(
            {"sub": "test", "aud": "authenticated"},
            rsa_private_key_pem,
            algorithm="RS256",
            headers={"kid": "non-existent-kid"},
        )

        with patch("app.core.auth.get_jwks", new_callable=AsyncMock) as mock_get_jwks:
            mock_get_jwks.return_value = test_jwks

            result = await get_signing_key(token)

            # Should return first key as fallback
            assert result == test_jwks["keys"][0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_401_on_invalid_token_header(self) -> None:
        """Raises 401 for malformed token header."""
        with patch("app.core.auth.get_jwks", new_callable=AsyncMock) as mock_get_jwks:
            mock_get_jwks.return_value = {"keys": [{"kid": "test-key"}]}

            with pytest.raises(HTTPException) as exc_info:
                await get_signing_key("not.a.valid.token")

            assert exc_info.value.status_code == 401
            assert "Invalid token header" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_401_when_no_keys_in_jwks(self, valid_jwt_token) -> None:
        """Raises 401 when JWKS has no keys."""
        with patch("app.core.auth.get_jwks", new_callable=AsyncMock) as mock_get_jwks:
            mock_get_jwks.return_value = {"keys": []}

            with pytest.raises(HTTPException) as exc_info:
                await get_signing_key(valid_jwt_token)

            assert exc_info.value.status_code == 401
            assert "No matching signing key" in exc_info.value.detail


class TestDecodeSupabaseToken:
    """Tests for decode_supabase_token() function (now async)."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_decodes_valid_token(self, valid_jwt_token, test_jwks, valid_jwt_claims) -> None:
        """Successfully decodes a valid JWT token."""
        with patch("app.core.auth.get_signing_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            result = await decode_supabase_token(valid_jwt_token)

            assert result["sub"] == valid_jwt_claims["sub"]
            assert result["email"] == valid_jwt_claims["email"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_401_on_expired_token(self, expired_jwt_token, test_jwks) -> None:
        """Raises 401 for expired tokens."""
        with patch("app.core.auth.get_signing_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            with pytest.raises(HTTPException) as exc_info:
                await decode_supabase_token(expired_jwt_token)

            assert exc_info.value.status_code == 401
            assert "Invalid token" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_401_on_wrong_audience(self, wrong_audience_jwt_token, test_jwks) -> None:
        """Raises 401 for tokens with wrong audience."""
        with patch("app.core.auth.get_signing_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            with pytest.raises(HTTPException) as exc_info:
                await decode_supabase_token(wrong_audience_jwt_token)

            assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_401_on_invalid_signature(
        self, wrong_signature_jwt_token, test_jwks
    ) -> None:
        """Raises 401 for tokens with invalid signature."""
        with patch("app.core.auth.get_signing_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            with pytest.raises(HTTPException) as exc_info:
                await decode_supabase_token(wrong_signature_jwt_token)

            assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    """Tests for get_current_user() dependency."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_auth_user_with_valid_token(
        self, mock_bearer_credentials, valid_jwt_claims
    ) -> None:
        """Returns AuthUser for valid credentials."""
        with patch("app.core.auth.decode_supabase_token", new_callable=AsyncMock) as mock_decode:
            mock_decode.return_value = valid_jwt_claims

            result = await get_current_user(mock_bearer_credentials)

            assert isinstance(result, AuthUser)
            assert result.auth_id == valid_jwt_claims["sub"]
            assert result.email == valid_jwt_claims["email"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_401_when_no_credentials(self) -> None:
        """Raises 401 when no credentials provided."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_401_when_token_missing_sub(self, mock_bearer_credentials) -> None:
        """Raises 401 when token is missing 'sub' claim."""
        with patch("app.core.auth.decode_supabase_token", new_callable=AsyncMock) as mock_decode:
            mock_decode.return_value = {"email": "test@example.com"}  # No 'sub'

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_bearer_credentials)

            assert exc_info.value.status_code == 401
            assert "missing user ID" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_missing_email_gracefully(self, mock_bearer_credentials) -> None:
        """Returns empty email when email claim is missing."""
        with patch("app.core.auth.decode_supabase_token", new_callable=AsyncMock) as mock_decode:
            mock_decode.return_value = {"sub": "user-123"}  # No email

            result = await get_current_user(mock_bearer_credentials)

            assert result.auth_id == "user-123"
            assert result.email == ""


class TestGetOptionalUser:
    """Tests for get_optional_user() dependency."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_authenticated_user_with_valid_token(
        self, mock_bearer_credentials, valid_jwt_claims
    ) -> None:
        """Returns authenticated user for valid credentials."""
        with patch("app.core.auth.decode_supabase_token", new_callable=AsyncMock) as mock_decode:
            mock_decode.return_value = valid_jwt_claims

            result = await get_optional_user(mock_bearer_credentials)

            assert isinstance(result, AuthOptionalUser)
            assert result.is_authenticated is True
            assert result.auth_id == valid_jwt_claims["sub"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_unauthenticated_when_no_credentials(self) -> None:
        """Returns unauthenticated user when no credentials."""
        result = await get_optional_user(None)

        assert isinstance(result, AuthOptionalUser)
        assert result.is_authenticated is False
        assert result.auth_id is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_unauthenticated_on_invalid_token(self, mock_bearer_credentials) -> None:
        """Returns unauthenticated user when token is invalid."""
        with patch("app.core.auth.decode_supabase_token", new_callable=AsyncMock) as mock_decode:
            mock_decode.side_effect = HTTPException(status_code=401, detail="Invalid")

            result = await get_optional_user(mock_bearer_credentials)

            assert result.is_authenticated is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_unauthenticated_when_missing_sub(self, mock_bearer_credentials) -> None:
        """Returns unauthenticated when token missing 'sub'."""
        with patch("app.core.auth.decode_supabase_token", new_callable=AsyncMock) as mock_decode:
            mock_decode.return_value = {"email": "test@example.com"}  # No sub

            result = await get_optional_user(mock_bearer_credentials)

            assert result.is_authenticated is False


class TestGetUserFromState:
    """Tests for get_user_from_state() dependency."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_user_from_state(self, mock_request_authenticated) -> None:
        """Returns user attached to request.state."""
        result = await get_user_from_state(mock_request_authenticated)

        assert result.is_authenticated is True
        assert result.auth_id == "auth-user-uuid-12345"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_unauthenticated_when_no_user_in_state(self, mock_request) -> None:
        """Returns unauthenticated when state.user is None."""
        mock_request.state.user = None

        result = await get_user_from_state(mock_request)

        assert result.is_authenticated is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_unauthenticated_when_state_missing(self) -> None:
        """Returns unauthenticated when state attribute missing."""
        request = MagicMock()
        # Simulate missing user attribute
        request.state = MagicMock(spec=[])  # Empty spec means no attributes

        result = await get_user_from_state(request)

        assert result.is_authenticated is False


class TestRequireAuthFromState:
    """Tests for require_auth_from_state() dependency."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_auth_user_when_authenticated(self, mock_request_authenticated) -> None:
        """Returns AuthUser when request has authenticated user."""
        with patch("app.core.auth._deleted_user_cache") as mock_cache:
            mock_cache.is_deleted.return_value = False  # Not deleted
            result = await require_auth_from_state(mock_request_authenticated)

            assert isinstance(result, AuthUser)
            assert result.auth_id == "auth-user-uuid-12345"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_401_when_not_authenticated(self, mock_request_unauthenticated) -> None:
        """Raises 401 when user is not authenticated."""
        with pytest.raises(HTTPException) as exc_info:
            await require_auth_from_state(mock_request_unauthenticated)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_401_when_no_user_in_state(self, mock_request) -> None:
        """Raises 401 when state.user is None."""
        mock_request.state.user = None

        with pytest.raises(HTTPException) as exc_info:
            await require_auth_from_state(mock_request)

        assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_includes_token_error_in_detail(self, mock_request_with_token_error) -> None:
        """Includes token error message in 401 detail."""
        with pytest.raises(HTTPException) as exc_info:
            await require_auth_from_state(mock_request_with_token_error)

        assert "Token expired" in exc_info.value.detail


class TestAuthUserModel:
    """Tests for AuthUser Pydantic model."""

    @pytest.mark.unit
    def test_creates_auth_user(self) -> None:
        """Creates AuthUser with required fields."""
        user = AuthUser(auth_id="123", email="test@example.com")

        assert user.auth_id == "123"
        assert user.email == "test@example.com"

    @pytest.mark.unit
    def test_auth_user_requires_auth_id(self) -> None:
        """AuthUser requires auth_id field."""
        with pytest.raises(ValidationError):
            AuthUser(email="test@example.com")  # type: ignore

    @pytest.mark.unit
    def test_auth_user_requires_email(self) -> None:
        """AuthUser requires email field."""
        with pytest.raises(ValidationError):
            AuthUser(auth_id="123")  # type: ignore


class TestAuthOptionalUserModel:
    """Tests for AuthOptionalUser Pydantic model."""

    @pytest.mark.unit
    def test_creates_unauthenticated_by_default(self) -> None:
        """Creates unauthenticated user by default."""
        user = AuthOptionalUser()

        assert user.is_authenticated is False
        assert user.auth_id is None
        assert user.email is None

    @pytest.mark.unit
    def test_creates_authenticated_user(self) -> None:
        """Creates authenticated user with all fields."""
        user = AuthOptionalUser(auth_id="123", email="test@example.com", is_authenticated=True)

        assert user.is_authenticated is True
        assert user.auth_id == "123"
        assert user.email == "test@example.com"


class TestDeletedUserCache:
    """Test the deleted user cache."""

    @pytest.mark.unit
    def test_cache_returns_none_for_unknown_user(self) -> None:
        """Cache returns None for users not in cache."""
        from app.core.auth import DeletedUserCache

        cache = DeletedUserCache()
        assert cache.is_deleted("unknown-user") is None

    @pytest.mark.unit
    def test_cache_stores_deleted_status(self) -> None:
        """Cache stores and returns deleted status."""
        from app.core.auth import DeletedUserCache

        cache = DeletedUserCache()
        cache.set("user-123", is_deleted=True)
        assert cache.is_deleted("user-123") is True

    @pytest.mark.unit
    def test_cache_stores_not_deleted_status(self) -> None:
        """Cache stores and returns not-deleted status."""
        from app.core.auth import DeletedUserCache

        cache = DeletedUserCache()
        cache.set("user-456", is_deleted=False)
        assert cache.is_deleted("user-456") is False

    @pytest.mark.unit
    def test_cache_expires_after_ttl(self) -> None:
        """Cache entries expire after TTL."""
        import time as time_module

        from app.core.auth import DeletedUserCache

        cache = DeletedUserCache(ttl_seconds=1)
        cache.set("user-789", is_deleted=True)
        assert cache.is_deleted("user-789") is True
        time_module.sleep(1.1)
        assert cache.is_deleted("user-789") is None


class TestRequireAuthDeletedUser:
    """Test that deleted users are rejected."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deleted_user_rejected(self) -> None:
        """Deleted user gets 401 even with valid token."""
        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.auth_id = "auth-123"
        mock_user.email = "test@example.com"
        mock_request.state.user = mock_user
        mock_request.state.token_error = None

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"deleted_at": "2026-01-01T00:00:00+00:00"}
        ]

        with patch("app.core.auth.get_supabase", return_value=mock_supabase):
            with patch("app.core.auth._deleted_user_cache") as mock_cache:
                mock_cache.is_deleted.return_value = None
                with pytest.raises(HTTPException) as exc_info:
                    await require_auth_from_state(mock_request)
                assert exc_info.value.status_code == 401
                assert "account" in exc_info.value.detail.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_active_user_allowed(self) -> None:
        """Active (not deleted) user is allowed through."""
        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.auth_id = "auth-456"
        mock_user.email = "active@example.com"
        mock_request.state.user = mock_user
        mock_request.state.token_error = None

        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"deleted_at": None}
        ]

        with patch("app.core.auth.get_supabase", return_value=mock_supabase):
            with patch("app.core.auth._deleted_user_cache") as mock_cache:
                mock_cache.is_deleted.return_value = None
                result = await require_auth_from_state(mock_request)
                assert result.auth_id == "auth-456"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_uses_cache_when_available(self) -> None:
        """Uses cache to avoid DB lookup when entry exists."""
        mock_request = MagicMock()
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.auth_id = "auth-789"
        mock_user.email = "cached@example.com"
        mock_request.state.user = mock_user
        mock_request.state.token_error = None

        mock_supabase = MagicMock()

        with patch("app.core.auth.get_supabase", return_value=mock_supabase):
            with patch("app.core.auth._deleted_user_cache") as mock_cache:
                mock_cache.is_deleted.return_value = False
                result = await require_auth_from_state(mock_request)
                assert result.auth_id == "auth-789"
                mock_supabase.table.assert_not_called()
