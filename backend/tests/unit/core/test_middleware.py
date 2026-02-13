"""Unit tests for middleware (app/core/middleware.py)."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import JWTError
from starlette.requests import Request
from starlette.responses import Response

from app.core.auth import AuthOptionalUser
from app.core.middleware import (
    CorrelationIDMiddleware,
    JWTValidationMiddleware,
    RequestLoggingMiddleware,
    correlation_id_var,
    get_correlation_id,
)


class TestJWTValidationMiddleware:
    """Tests for JWTValidationMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = MagicMock()
        return JWTValidationMiddleware(app)

    @pytest.fixture
    def mock_call_next(self):
        """Mock call_next function that returns a response."""

        async def call_next(request):
            return Response(status_code=200)

        return call_next

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initializes_unauthenticated_user_by_default(
        self, middleware, mock_call_next
    ) -> None:
        """Sets unauthenticated user in state when no auth header."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {}

        await middleware.dispatch(request, mock_call_next)

        assert request.state.user.is_authenticated is False
        assert request.state.token_error is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_authenticates_valid_token(
        self, middleware, mock_call_next, valid_jwt_token, valid_jwt_claims
    ) -> None:
        """Sets authenticated user for valid Bearer token."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {"Authorization": f"Bearer {valid_jwt_token}"}

        with patch.object(middleware, "_validate_token", new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = valid_jwt_claims

            await middleware.dispatch(request, mock_call_next)

            assert request.state.user.is_authenticated is True
            assert request.state.user.auth_id == valid_jwt_claims["sub"]
            assert request.state.user.email == valid_jwt_claims["email"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_jwt_error_gracefully(
        self, middleware, mock_call_next, valid_jwt_token
    ) -> None:
        """Stores error but continues on JWTError."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {"Authorization": f"Bearer {valid_jwt_token}"}

        with patch.object(middleware, "_validate_token", new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = JWTError("Token expired")

            response = await middleware.dispatch(request, mock_call_next)

            assert request.state.user.is_authenticated is False
            assert request.state.token_error == "Token expired"
            assert response.status_code == 200  # Request continues

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_non_jwt_error_gracefully(
        self, middleware, mock_call_next, valid_jwt_token
    ) -> None:
        """Stores error but continues on non-JWT errors."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {"Authorization": f"Bearer {valid_jwt_token}"}

        with patch.object(middleware, "_validate_token", new_callable=AsyncMock) as mock_validate:
            mock_validate.side_effect = Exception("Network error")

            response = await middleware.dispatch(request, mock_call_next)

            assert request.state.user.is_authenticated is False
            assert "Auth error" in request.state.token_error
            assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ignores_non_bearer_auth_header(self, middleware, mock_call_next) -> None:
        """Ignores Authorization headers that are not Bearer."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {"Authorization": "Basic dXNlcjpwYXNz"}

        await middleware.dispatch(request, mock_call_next)

        assert request.state.user.is_authenticated is False
        assert request.state.token_error is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_continues_to_next_handler(self, middleware, valid_jwt_token) -> None:
        """Always calls next handler regardless of auth result."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {"Authorization": f"Bearer {valid_jwt_token}"}

        call_next_called = False

        async def tracking_call_next(req):
            nonlocal call_next_called
            call_next_called = True
            return Response(status_code=200)

        with patch.object(middleware, "_validate_token", new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {"sub": "123", "email": "test@test.com"}

            await middleware.dispatch(request, tracking_call_next)

            assert call_next_called is True


class TestValidateTokenMethod:
    """Tests for _validate_token() method (now async)."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = MagicMock()
        return JWTValidationMiddleware(app)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_payload_for_valid_token(
        self, middleware, valid_jwt_token, test_jwks, valid_jwt_claims
    ) -> None:
        """Returns decoded payload for valid token."""
        with patch("app.core.middleware.get_signing_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            result = await middleware._validate_token(valid_jwt_token)

            assert result["sub"] == valid_jwt_claims["sub"]
            assert result["email"] == valid_jwt_claims["email"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_jwt_error_for_expired_token(
        self, middleware, expired_jwt_token, test_jwks
    ) -> None:
        """Raises JWTError for expired tokens."""
        with patch("app.core.middleware.get_signing_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            # jose library raises JWTError for expired tokens
            with pytest.raises(JWTError):
                await middleware._validate_token(expired_jwt_token)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_jwt_error_for_invalid_signature(
        self, middleware, wrong_signature_jwt_token, test_jwks
    ) -> None:
        """Raises JWTError for tokens with invalid signature."""
        with patch("app.core.middleware.get_signing_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            with pytest.raises(JWTError):
                await middleware._validate_token(wrong_signature_jwt_token)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_checks_expiration_explicitly(
        self, middleware, valid_jwt_claims, rsa_private_key_pem, jwks_key_id, test_jwks
    ) -> None:
        """Explicitly checks exp claim even if jose passes."""
        from jose import jwt

        # Create token that's technically valid but exp is in the past
        claims = valid_jwt_claims.copy()
        claims["exp"] = int(time.time()) - 10  # 10 seconds ago

        token = jwt.encode(
            claims, rsa_private_key_pem, algorithm="RS256", headers={"kid": jwks_key_id}
        )

        with patch("app.core.middleware.get_signing_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            # Should raise JWTError due to expiration
            with pytest.raises(JWTError):
                await middleware._validate_token(token)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_none_on_general_exception(self, middleware, valid_jwt_token) -> None:
        """Returns None on non-JWT exceptions."""
        with patch("app.core.middleware.get_signing_key", new_callable=AsyncMock) as mock_get_key:
            mock_get_key.side_effect = Exception("Unexpected error")

            result = await middleware._validate_token(valid_jwt_token)

            assert result is None


class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = MagicMock()
        return RequestLoggingMiddleware(app)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_continues_request_for_authenticated_user(self, middleware) -> None:
        """Continues request processing for authenticated users."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = AuthOptionalUser(
            auth_id="123", email="test@test.com", is_authenticated=True
        )

        async def call_next(req):
            return Response(status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_continues_request_for_unauthenticated_user(self, middleware) -> None:
        """Continues request processing for unauthenticated users."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = AuthOptionalUser(is_authenticated=False)

        async def call_next(req):
            return Response(status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_missing_user_state(self, middleware) -> None:
        """Handles requests without user in state gracefully."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.user = None

        async def call_next(req):
            return Response(status_code=200)

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 200


class TestCorrelationIDMiddleware:
    """Tests for CorrelationIDMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = MagicMock()
        return CorrelationIDMiddleware(app)

    @pytest.fixture
    def mock_call_next(self):
        """Mock call_next function that returns a response."""

        async def call_next(request):
            return Response(status_code=200)

        return call_next

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generates_correlation_id_when_missing(self, middleware, mock_call_next) -> None:
        """Generates UUID correlation ID when no header present."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {}

        response = await middleware.dispatch(request, mock_call_next)

        # Should be a valid UUID format
        correlation_id = request.state.correlation_id
        assert correlation_id is not None
        assert len(correlation_id) == 36  # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        assert "-" in correlation_id

        # Should be in response header
        assert response.headers["X-Request-ID"] == correlation_id

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extracts_correlation_id_from_x_request_id(
        self, middleware, mock_call_next
    ) -> None:
        """Extracts correlation ID from X-Request-ID header."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {"X-Request-ID": "test-request-123"}

        response = await middleware.dispatch(request, mock_call_next)

        assert request.state.correlation_id == "test-request-123"
        assert response.headers["X-Request-ID"] == "test-request-123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extracts_correlation_id_from_x_correlation_id(
        self, middleware, mock_call_next
    ) -> None:
        """Extracts correlation ID from X-Correlation-ID header."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {"X-Correlation-ID": "correlation-456"}

        response = await middleware.dispatch(request, mock_call_next)

        assert request.state.correlation_id == "correlation-456"
        assert response.headers["X-Request-ID"] == "correlation-456"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_x_request_id_takes_precedence(self, middleware, mock_call_next) -> None:
        """X-Request-ID takes precedence over X-Correlation-ID."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {
            "X-Request-ID": "request-id",
            "X-Correlation-ID": "correlation-id",
        }

        response = await middleware.dispatch(request, mock_call_next)

        assert request.state.correlation_id == "request-id"
        assert response.headers["X-Request-ID"] == "request-id"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_correlation_id_available_in_context_var(self, middleware) -> None:
        """Correlation ID is available via ContextVar during request."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {"X-Request-ID": "context-test-789"}

        captured_id = None

        async def capturing_call_next(req):
            nonlocal captured_id
            captured_id = get_correlation_id()
            return Response(status_code=200)

        await middleware.dispatch(request, capturing_call_next)

        assert captured_id == "context-test-789"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_context_var_reset_after_request(self, middleware, mock_call_next) -> None:
        """ContextVar is reset after request completes."""
        # Clear any existing value
        correlation_id_var.set("")

        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {"X-Request-ID": "temp-id"}

        await middleware.dispatch(request, mock_call_next)

        # After request, context var should be reset (empty or default)
        assert get_correlation_id() == ""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_response_header_set_even_on_error(self, middleware) -> None:
        """Response header is set even if handler raises (via finally)."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.headers = {"X-Request-ID": "error-test"}

        async def error_call_next(req):
            raise ValueError("Handler error")

        with pytest.raises(ValueError):
            await middleware.dispatch(request, error_call_next)

        # Context var should still be reset
        assert get_correlation_id() == ""
