"""
Authentication module for Supabase JWT validation.

Provides FastAPI dependencies for extracting and validating
JWT tokens from Supabase Auth using JWKS (asymmetric keys).
"""

from typing import Optional
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
from pydantic import BaseModel
import json
from functools import lru_cache

from app.core.config import get_settings

settings = get_settings()

# HTTP Bearer token extraction
security = HTTPBearer(auto_error=False)

# Cache for JWKS keys
_jwks_cache: Optional[dict] = None


class AuthUser(BaseModel):
    """Authenticated user context from JWT token."""
    auth_id: str  # Supabase auth.uid()
    email: str
    # Add more claims as needed


class AuthOptionalUser(BaseModel):
    """Optional authenticated user (for endpoints that work with or without auth)."""
    auth_id: Optional[str] = None
    email: Optional[str] = None
    is_authenticated: bool = False


def get_jwks() -> dict:
    """
    Fetch JWKS (JSON Web Key Set) from Supabase's well-known endpoint.
    Keys are cached to avoid repeated network calls.
    """
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    try:
        response = httpx.get(jwks_url, timeout=10.0)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch JWKS: {str(e)}"
        )


def get_signing_key(token: str) -> dict:
    """
    Get the signing key from JWKS that matches the token's key ID (kid).
    """
    jwks = get_jwks()

    # Get the key ID from the token header
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    kid = unverified_header.get("kid")

    # Find matching key in JWKS
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    # If no kid match, try the first key (some Supabase projects may not use kid)
    if jwks.get("keys"):
        return jwks["keys"][0]

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No matching signing key found",
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_supabase_token(token: str) -> dict:
    """
    Decode and validate a Supabase JWT token using JWKS.

    Supabase JWTs contain:
    - sub: user's auth_id (UUID)
    - email: user's email
    - aud: "authenticated" for logged-in users
    - role: "authenticated" or "anon"
    """
    try:
        signing_key = get_signing_key(token)

        # Decode using the public key from JWKS
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],  # Supabase uses RS256 or ES256
            audience="authenticated"
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthUser:
    """
    FastAPI dependency to get the current authenticated user.

    Usage:
        @router.get("/protected")
        async def protected_route(user: AuthUser = Depends(get_current_user)):
            return {"user_id": user.auth_id}
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_supabase_token(credentials.credentials)

    # Extract user info from JWT claims
    auth_id = payload.get("sub")
    email = payload.get("email")

    if not auth_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(auth_id=auth_id, email=email or "")


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> AuthOptionalUser:
    """
    FastAPI dependency to get an optional authenticated user.

    Returns an unauthenticated user object if no valid token is provided,
    allowing endpoints to work for both authenticated and anonymous users.

    Usage:
        @router.get("/public-or-private")
        async def flexible_route(user: AuthOptionalUser = Depends(get_optional_user)):
            if user.is_authenticated:
                return {"message": f"Hello, {user.email}"}
            return {"message": "Hello, anonymous user"}
    """
    if credentials is None:
        return AuthOptionalUser(is_authenticated=False)

    try:
        payload = decode_supabase_token(credentials.credentials)
        auth_id = payload.get("sub")
        email = payload.get("email")

        if auth_id:
            return AuthOptionalUser(
                auth_id=auth_id,
                email=email,
                is_authenticated=True
            )
    except HTTPException:
        pass

    return AuthOptionalUser(is_authenticated=False)
