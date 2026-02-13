"""
Middleware for FastAPI.

Contains:
- CorrelationIDMiddleware: Extracts/generates request correlation IDs
- JWTValidationMiddleware: Validates JWT tokens and attaches user context
"""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Optional

from fastapi import Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.auth import AuthOptionalUser, get_signing_key

logger = logging.getLogger(__name__)

# Context variable for correlation ID - accessible from any async context
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get the current correlation ID from context."""
    return correlation_id_var.get()


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts or generates a correlation ID for each request.

    The correlation ID is:
    1. Extracted from X-Request-ID or X-Correlation-ID header if present
    2. Generated as a UUID if not present
    3. Stored in request.state.correlation_id for route handlers
    4. Stored in ContextVar for logging filter access
    5. Returned in X-Request-ID response header

    Usage in routes:
        @router.get("/example")
        async def example(request: Request):
            return {"correlation_id": request.state.correlation_id}
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract from headers or generate
        correlation_id = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-Correlation-ID")
            or str(uuid.uuid4())
        )

        # Store in request state (for route handlers)
        request.state.correlation_id = correlation_id

        # Store in context var (for logging)
        token = correlation_id_var.set(correlation_id)

        try:
            response = await call_next(request)
            # Add to response headers
            response.headers["X-Request-ID"] = correlation_id
            return response
        finally:
            # Reset context var
            correlation_id_var.reset(token)


class JWTValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates JWT tokens and attaches user context to requests.

    This middleware:
    1. Extracts Bearer token from Authorization header
    2. Validates the token using Supabase JWKS
    3. Attaches user info to request.state.user
    4. Continues processing even without valid auth (for public endpoints)

    Usage in routes:
        @router.get("/example")
        async def example(request: Request):
            if request.state.user.is_authenticated:
                return {"user": request.state.user.auth_id}
            return {"message": "anonymous"}
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Initialize with unauthenticated user
        request.state.user = AuthOptionalUser(is_authenticated=False)
        request.state.token_error = None

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix

            try:
                # Validate and decode token (now async)
                user_info = await self._validate_token(token)
                if user_info:
                    request.state.user = AuthOptionalUser(
                        auth_id=user_info.get("sub"),
                        email=user_info.get("email"),
                        is_authenticated=True,
                    )
            except JWTError as e:
                # Store error for potential logging/debugging
                request.state.token_error = str(e)
            except Exception as e:
                # Non-JWT errors (network issues fetching JWKS, etc.)
                request.state.token_error = f"Auth error: {str(e)}"

        # Continue processing request
        response = await call_next(request)
        return response

    async def _validate_token(self, token: str) -> Optional[dict]:
        """
        Validate JWT token and return payload if valid.

        Returns None if token is invalid or expired.
        """
        try:
            signing_key = await get_signing_key(token)

            payload = jwt.decode(
                token, signing_key, algorithms=["RS256", "ES256"], audience="authenticated"
            )

            # Check expiration explicitly (jose should handle this, but be safe)
            exp = payload.get("exp")
            if exp and time.time() > exp:
                return None

            return payload

        except JWTError:
            raise
        except Exception:
            return None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Optional middleware for logging authenticated requests.

    Useful for debugging and audit trails.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Log request info if user is authenticated
        user = getattr(request.state, "user", None)

        if user and user.is_authenticated:
            logger.debug(
                "Authenticated request: %s -> %s %s",
                user.auth_id,
                request.method,
                request.url.path,
            )

        response = await call_next(request)
        return response
