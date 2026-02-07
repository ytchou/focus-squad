"""Integration tests for auth flow (end-to-end)."""

from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.auth import (
    AuthOptionalUser,
    AuthUser,
    get_user_from_state,
    require_auth_from_state,
)
from app.core.middleware import JWTValidationMiddleware


@pytest.fixture
def test_app() -> None:
    """Create test FastAPI app with auth middleware."""
    app = FastAPI()
    app.add_middleware(JWTValidationMiddleware)

    @app.get("/public")
    async def public_route():
        return {"message": "public"}

    @app.get("/optional-auth")
    async def optional_auth_route(user: AuthOptionalUser = Depends(get_user_from_state)):
        return {
            "authenticated": user.is_authenticated,
            "auth_id": user.auth_id,
        }

    @app.get("/protected")
    async def protected_route(user: AuthUser = Depends(require_auth_from_state)):
        return {
            "auth_id": user.auth_id,
            "email": user.email,
        }

    return app


@pytest.fixture
def client(test_app):
    """Test client for the app."""
    return TestClient(test_app)


class TestPublicEndpoints:
    """Tests for public endpoints without auth."""

    @pytest.mark.integration
    def test_public_route_accessible_without_auth(self, client) -> None:
        """Public routes work without authentication."""
        response = client.get("/public")

        assert response.status_code == 200
        assert response.json()["message"] == "public"


class TestOptionalAuthEndpoints:
    """Tests for endpoints with optional authentication."""

    @pytest.mark.integration
    def test_optional_auth_without_token(self, client) -> None:
        """Returns unauthenticated user when no token."""
        response = client.get("/optional-auth")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["auth_id"] is None

    @pytest.mark.integration
    def test_optional_auth_with_valid_token(
        self, client, valid_jwt_token, test_jwks, valid_jwt_claims
    ) -> None:
        """Returns authenticated user with valid token."""
        with patch("app.core.middleware.get_signing_key") as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            response = client.get(
                "/optional-auth", headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["auth_id"] == valid_jwt_claims["sub"]

    @pytest.mark.integration
    def test_optional_auth_with_invalid_token(self, client) -> None:
        """Returns unauthenticated user with invalid token."""
        response = client.get(
            "/optional-auth", headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False


class TestProtectedEndpoints:
    """Tests for protected endpoints requiring authentication."""

    @pytest.mark.integration
    def test_protected_route_without_token(self, client) -> None:
        """Returns 401 when no token provided."""
        response = client.get("/protected")

        assert response.status_code == 401

    @pytest.mark.integration
    def test_protected_route_with_valid_token(
        self, client, valid_jwt_token, test_jwks, valid_jwt_claims
    ) -> None:
        """Returns user data with valid token."""
        with patch("app.core.middleware.get_signing_key") as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            response = client.get(
                "/protected", headers={"Authorization": f"Bearer {valid_jwt_token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["auth_id"] == valid_jwt_claims["sub"]
            assert data["email"] == valid_jwt_claims["email"]

    @pytest.mark.integration
    def test_protected_route_with_expired_token(self, client, expired_jwt_token, test_jwks) -> None:
        """Returns 401 with expired token."""
        with patch("app.core.middleware.get_signing_key") as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            response = client.get(
                "/protected", headers={"Authorization": f"Bearer {expired_jwt_token}"}
            )

            assert response.status_code == 401

    @pytest.mark.integration
    def test_protected_route_with_malformed_token(self, client) -> None:
        """Returns 401 with malformed token."""
        response = client.get("/protected", headers={"Authorization": "Bearer not.a.jwt"})

        assert response.status_code == 401

    @pytest.mark.integration
    def test_protected_route_with_wrong_signature(
        self, client, wrong_signature_jwt_token, test_jwks
    ) -> None:
        """Returns 401 with wrong signature token."""
        with patch("app.core.middleware.get_signing_key") as mock_get_key:
            mock_get_key.return_value = test_jwks["keys"][0]

            response = client.get(
                "/protected",
                headers={"Authorization": f"Bearer {wrong_signature_jwt_token}"},
            )

            assert response.status_code == 401
