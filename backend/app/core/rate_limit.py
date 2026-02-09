"""
Rate limiting configuration using slowapi.

Uses auth_id for authenticated users, client IP for anonymous.
Backed by Redis in production for multi-process deployments.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings


def _get_rate_limit_key(request: Request) -> str:
    """
    Extract rate limit key from request.

    Priority:
    1. Authenticated user -> "auth:{auth_id}"
    2. Anonymous -> "ip:{client_ip}"
    """
    user_state = getattr(request.state, "user", None)
    if user_state and hasattr(user_state, "auth_id"):
        return f"auth:{user_state.auth_id}"

    # Fallback to IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=["60/minute"],
    enabled=get_settings().rate_limit_enabled,
    storage_uri=get_settings().redis_url,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors with a standardized response."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "code": "RATE_LIMIT_EXCEEDED",
        },
    )
