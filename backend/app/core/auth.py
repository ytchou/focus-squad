"""
Authentication module for Supabase JWT validation.

Provides FastAPI dependencies for extracting and validating
JWT tokens from Supabase Auth using JWKS (asymmetric keys).

Two modes of operation:
1. Standalone: Dependencies validate tokens directly (legacy)
2. With middleware: Dependencies read from request.state (recommended)
"""

import asyncio
import logging
import time
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.database import get_supabase

settings = get_settings()
logger = logging.getLogger(__name__)

# HTTP Bearer token extraction
security = HTTPBearer(auto_error=False)


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


class JWKSCache:
    """
    JWKS cache with TTL and background refresh.

    Features:
    - Caches JWKS keys for 1 hour (TTL=3600s)
    - Triggers background refresh 5 minutes before expiry (REFRESH_BEFORE=300s)
    - Uses asyncio.Lock to prevent concurrent fetches
    - Keeps old keys if background refresh fails
    """

    TTL: int = 3600  # 1 hour in seconds
    REFRESH_BEFORE: int = 300  # 5 minutes before expiry

    def __init__(self) -> None:
        self._keys: Optional[dict] = None
        self._fetched_at: Optional[float] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._lock: Optional[asyncio.Lock] = None  # Lazy init to avoid event loop issues

    def _get_lock(self) -> asyncio.Lock:
        """Get or create the asyncio lock (lazy initialization)."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def get_keys(self) -> dict:
        """
        Get JWKS keys, fetching or refreshing as needed.

        Returns cached keys if fresh, triggers background refresh if
        within refresh window, or does synchronous fetch if expired.
        """
        now = time.time()

        # Case 1: Fresh cache - return immediately
        if self._is_fresh(now):
            assert self._keys is not None  # Guaranteed by _is_fresh check
            return self._keys

        # Case 2: Within refresh window - return old keys, refresh in background
        if self._should_refresh_in_background(now):
            self._schedule_background_refresh()
            assert self._keys is not None  # Guaranteed by _should_refresh_in_background check
            return self._keys

        # Case 3: Expired or empty - synchronous fetch
        async with self._get_lock():
            # Double-check after acquiring lock (another task may have fetched)
            if self._is_fresh(time.time()):
                assert self._keys is not None  # Guaranteed by _is_fresh check
                return self._keys

            self._keys = await self._fetch_keys()
            self._fetched_at = time.time()
            return self._keys

    def _is_fresh(self, now: float) -> bool:
        """Check if cache is fresh (within TTL)."""
        if self._keys is None or self._fetched_at is None:
            return False
        age = now - self._fetched_at
        return age < (self.TTL - self.REFRESH_BEFORE)

    def _should_refresh_in_background(self, now: float) -> bool:
        """Check if we're within the refresh window (old but not expired)."""
        if self._keys is None or self._fetched_at is None:
            return False
        age = now - self._fetched_at
        # Within refresh window: TTL - REFRESH_BEFORE <= age < TTL
        return (self.TTL - self.REFRESH_BEFORE) <= age < self.TTL

    def _schedule_background_refresh(self) -> None:
        """Spawn a background task to refresh keys."""
        # Don't spawn if there's already a refresh in progress
        if self._refresh_task is not None and not self._refresh_task.done():
            return

        # Log if previous task failed (for debugging)
        if self._refresh_task is not None and self._refresh_task.done():
            exc = self._refresh_task.exception()
            if exc is not None:
                logger.debug(f"Previous background refresh failed: {exc}")

        self._refresh_task = asyncio.create_task(self._background_refresh())

    async def _background_refresh(self) -> None:
        """Refresh keys in the background, keeping old keys on failure."""
        try:
            async with self._get_lock():
                new_keys = await self._fetch_keys()
                self._keys = new_keys
                self._fetched_at = time.time()
                logger.info("JWKS cache refreshed in background")
        except Exception as e:
            # Keep old keys on failure
            logger.warning(f"Background JWKS refresh failed, keeping old keys: {e}")

    async def _fetch_keys(self) -> dict:
        """Fetch JWKS from Supabase's well-known endpoint."""
        jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_url, timeout=10.0)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to fetch JWKS: {str(e)}",
            )

    def invalidate(self) -> None:
        """Invalidate the cache, forcing a fresh fetch on next access."""
        self._keys = None
        self._fetched_at = None


# Global JWKS cache instance
_jwks_cache = JWKSCache()


class DeletedUserCache:
    """
    Simple in-memory cache for deleted user status.

    Caches whether a user's account is deleted to avoid
    DB lookup on every authenticated request.
    """

    TTL: int = 60  # 60 seconds (matches JWKSCache naming pattern)

    def __init__(self, ttl_seconds: int = TTL):
        self._cache: dict[str, tuple[bool, float]] = {}
        self._ttl = ttl_seconds

    def is_deleted(self, auth_id: str) -> Optional[bool]:
        """
        Check if user is deleted (from cache).

        Returns:
            True if deleted, False if not deleted, None if not in cache
        """
        entry = self._cache.get(auth_id)
        if entry is None:
            return None

        is_deleted, expires_at = entry
        if time.time() > expires_at:
            # Use pop() to avoid race condition if entry was already removed
            self._cache.pop(auth_id, None)
            return None

        return is_deleted

    def set(self, auth_id: str, is_deleted: bool) -> None:
        """Cache the deleted status for a user."""
        expires_at = time.time() + self._ttl
        self._cache[auth_id] = (is_deleted, expires_at)


# Global deleted user cache instance
_deleted_user_cache = DeletedUserCache()


async def get_jwks() -> dict:
    """
    Fetch JWKS (JSON Web Key Set) from Supabase's well-known endpoint.
    Keys are cached with TTL and background refresh.
    """
    return await _jwks_cache.get_keys()


async def get_signing_key(token: str) -> dict:
    """
    Get the signing key from JWKS that matches the token's key ID (kid).
    """
    jwks = await get_jwks()

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


async def decode_supabase_token(token: str) -> dict:
    """
    Decode and validate a Supabase JWT token using JWKS.

    Supabase JWTs contain:
    - sub: user's auth_id (UUID)
    - email: user's email
    - aud: "authenticated" for logged-in users
    - role: "authenticated" or "anon"
    """
    try:
        signing_key = await get_signing_key(token)

        # Decode using the public key from JWKS
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],  # Supabase uses RS256 or ES256
            audience="authenticated",
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
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

    payload = await decode_supabase_token(credentials.credentials)

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
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
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
        payload = await decode_supabase_token(credentials.credentials)
        auth_id = payload.get("sub")
        email = payload.get("email")

        if auth_id:
            return AuthOptionalUser(auth_id=auth_id, email=email, is_authenticated=True)
    except HTTPException:
        pass

    return AuthOptionalUser(is_authenticated=False)


async def get_user_from_state(request: Request) -> AuthOptionalUser:
    """
    Get user from request.state (populated by JWTValidationMiddleware).

    This is more efficient than get_current_user/get_optional_user as
    it avoids re-validating the token when middleware has already done so.

    Usage:
        @router.get("/example")
        async def example(user: AuthOptionalUser = Depends(get_user_from_state)):
            if user.is_authenticated:
                return {"user_id": user.auth_id}
            return {"message": "anonymous"}
    """
    user = getattr(request.state, "user", None)
    if user is not None:
        return user
    return AuthOptionalUser(is_authenticated=False)


async def require_auth_from_state(request: Request) -> AuthUser:
    """
    Require authenticated user from request.state (populated by middleware).

    Raises 401 if user is not authenticated or if account is deleted.

    Usage:
        @router.get("/protected")
        async def protected(user: AuthUser = Depends(require_auth_from_state)):
            return {"user_id": user.auth_id}
    """
    user = getattr(request.state, "user", None)

    if user is None or not user.is_authenticated:
        # Check if there was a token error for better error messages
        token_error = getattr(request.state, "token_error", None)
        detail = "Authentication required"
        if token_error:
            detail = f"Authentication failed: {token_error}"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user's account is deleted (with cache)
    cached_deleted = _deleted_user_cache.is_deleted(user.auth_id)

    if cached_deleted is None:
        # Cache miss - check database
        try:
            supabase = get_supabase()
            result = (
                supabase.table("users").select("deleted_at").eq("auth_id", user.auth_id).execute()
            )

            is_deleted = False
            # Explicit length check for clarity (empty list is falsy, but be explicit)
            if result.data and len(result.data) > 0 and result.data[0].get("deleted_at"):
                is_deleted = True

            _deleted_user_cache.set(user.auth_id, is_deleted)
            cached_deleted = is_deleted
        except Exception as e:
            # On database error, log and fail-open (allow request)
            # This prevents auth outage during transient DB issues
            logger.warning(f"Failed to check deleted status for user {user.auth_id}: {e}")
            cached_deleted = False

    if cached_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account has been deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthUser(auth_id=user.auth_id, email=user.email or "")
