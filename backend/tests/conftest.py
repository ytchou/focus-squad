"""Shared pytest fixtures for test suite."""

import base64
import time
from typing import Optional
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt


# =============================================================================
# RSA Key Fixtures (for RS256 JWT signing/verification)
# =============================================================================


@pytest.fixture(scope="session")
def rsa_key_pair():
    """
    Generate RSA key pair for testing RS256 JWTs.

    Session-scoped for efficiency - keys are expensive to generate.
    Returns (private_key, public_key) tuple.
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture(scope="session")
def rsa_private_key_pem(rsa_key_pair):
    """PEM-encoded private key for signing JWTs."""
    private_key, _ = rsa_key_pair
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@pytest.fixture(scope="session")
def rsa_public_key_pem(rsa_key_pair):
    """PEM-encoded public key for verifying JWTs."""
    _, public_key = rsa_key_pair
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


# =============================================================================
# JWKS Fixtures (JSON Web Key Set format for Supabase-style verification)
# =============================================================================


@pytest.fixture(scope="session")
def jwks_key_id() -> str:
    """Key ID (kid) used in test JWKS."""
    return "test-key-id-001"


@pytest.fixture(scope="session")
def test_jwks(rsa_key_pair, jwks_key_id):
    """
    Generate JWKS (JSON Web Key Set) from test RSA public key.

    Mimics Supabase's JWKS endpoint response format.
    """

    _, public_key = rsa_key_pair
    public_numbers = public_key.public_numbers()

    # Convert integers to base64url-encoded bytes
    def int_to_base64url(value: int, length: int) -> str:
        value_bytes = value.to_bytes(length, byteorder="big")
        return base64.urlsafe_b64encode(value_bytes).rstrip(b"=").decode("ascii")

    # RSA modulus (n) and exponent (e) in base64url format
    n = int_to_base64url(public_numbers.n, 256)  # 2048-bit key = 256 bytes
    e = int_to_base64url(public_numbers.e, 3)  # e=65537 fits in 3 bytes

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": jwks_key_id,
                "n": n,
                "e": e,
            }
        ]
    }


# =============================================================================
# JWT Token Fixtures
# =============================================================================


@pytest.fixture
def valid_jwt_claims():
    """Standard valid JWT claims for a Supabase authenticated user."""
    return {
        "sub": "auth-user-uuid-12345",
        "email": "testuser@example.com",
        "aud": "authenticated",
        "role": "authenticated",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,  # 1 hour from now
    }


@pytest.fixture
def expired_jwt_claims(valid_jwt_claims):
    """JWT claims that are already expired."""
    claims = valid_jwt_claims.copy()
    claims["exp"] = int(time.time()) - 3600  # 1 hour ago
    claims["iat"] = int(time.time()) - 7200  # 2 hours ago
    return claims


@pytest.fixture
def missing_sub_jwt_claims(valid_jwt_claims):
    """JWT claims missing the 'sub' (user ID) field."""
    claims = valid_jwt_claims.copy()
    del claims["sub"]
    return claims


@pytest.fixture
def wrong_audience_jwt_claims(valid_jwt_claims):
    """JWT claims with wrong audience."""
    claims = valid_jwt_claims.copy()
    claims["aud"] = "anon"  # Should be "authenticated"
    return claims


def create_test_jwt(claims: dict, private_key_pem: bytes, kid: str) -> str:
    """
    Helper function to create a signed JWT token.

    Args:
        claims: JWT payload claims
        private_key_pem: PEM-encoded RSA private key
        kid: Key ID to include in header

    Returns:
        Signed JWT string
    """
    return jwt.encode(claims, private_key_pem, algorithm="RS256", headers={"kid": kid})


@pytest.fixture
def valid_jwt_token(valid_jwt_claims, rsa_private_key_pem, jwks_key_id):
    """Generate a valid, signed JWT token."""
    return create_test_jwt(valid_jwt_claims, rsa_private_key_pem, jwks_key_id)


@pytest.fixture
def expired_jwt_token(expired_jwt_claims, rsa_private_key_pem, jwks_key_id):
    """Generate an expired JWT token."""
    return create_test_jwt(expired_jwt_claims, rsa_private_key_pem, jwks_key_id)


@pytest.fixture
def missing_sub_jwt_token(missing_sub_jwt_claims, rsa_private_key_pem, jwks_key_id):
    """Generate a JWT token missing the 'sub' claim."""
    return create_test_jwt(missing_sub_jwt_claims, rsa_private_key_pem, jwks_key_id)


@pytest.fixture
def wrong_audience_jwt_token(wrong_audience_jwt_claims, rsa_private_key_pem, jwks_key_id):
    """Generate a JWT token with wrong audience."""
    return create_test_jwt(wrong_audience_jwt_claims, rsa_private_key_pem, jwks_key_id)


@pytest.fixture
def malformed_jwt_token():
    """A malformed JWT token (not valid structure)."""
    return "not.a.valid.jwt.token"


@pytest.fixture
def wrong_signature_jwt_token(valid_jwt_claims, jwks_key_id):
    """JWT signed with a different key (signature won't verify)."""
    # Generate a different key pair
    different_private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    different_private_key_pem = different_private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return create_test_jwt(valid_jwt_claims, different_private_key_pem, jwks_key_id)


# =============================================================================
# Mock Request Fixtures
# =============================================================================


@pytest.fixture
def mock_request():
    """Create a mock FastAPI Request object."""
    request = MagicMock(spec=Request)
    request.state = MagicMock()
    request.headers = {}
    return request


@pytest.fixture
def mock_request_with_auth(mock_request, valid_jwt_token):
    """Mock request with valid Authorization header."""
    mock_request.headers = {"Authorization": f"Bearer {valid_jwt_token}"}
    return mock_request


@pytest.fixture
def mock_request_authenticated(mock_request):
    """Mock request with authenticated user in state (post-middleware)."""
    from app.core.auth import AuthOptionalUser

    mock_request.state.user = AuthOptionalUser(
        auth_id="auth-user-uuid-12345", email="testuser@example.com", is_authenticated=True
    )
    mock_request.state.token_error = None
    return mock_request


@pytest.fixture
def mock_request_unauthenticated(mock_request):
    """Mock request with unauthenticated user in state."""
    from app.core.auth import AuthOptionalUser

    mock_request.state.user = AuthOptionalUser(is_authenticated=False)
    mock_request.state.token_error = None
    return mock_request


@pytest.fixture
def mock_request_with_token_error(mock_request):
    """Mock request with a token error in state."""
    from app.core.auth import AuthOptionalUser

    mock_request.state.user = AuthOptionalUser(is_authenticated=False)
    mock_request.state.token_error = "Token expired"
    return mock_request


# =============================================================================
# Mock HTTP Bearer Credentials
# =============================================================================


@pytest.fixture
def mock_bearer_credentials(valid_jwt_token):
    """Mock HTTPAuthorizationCredentials object."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=valid_jwt_token)


@pytest.fixture
def mock_bearer_credentials_expired(expired_jwt_token):
    """Mock credentials with expired token."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_jwt_token)


# =============================================================================
# JWKS Cache Reset Fixture
# =============================================================================


@pytest.fixture(autouse=True)
def reset_jwks_cache():
    """Reset JWKS cache before each test to ensure isolation."""
    import app.core.auth as auth_module

    auth_module._jwks_cache = None
    yield
    auth_module._jwks_cache = None


# =============================================================================
# Mock Supabase Client
# =============================================================================


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client for database operations."""
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.eq.return_value = mock
    mock.single.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.execute.return_value = MagicMock(data=None)
    return mock


# =============================================================================
# Settings Override Fixture
# =============================================================================


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.supabase_url = "https://test-project.supabase.co"
    settings.supabase_anon_key = "test-anon-key"
    return settings
