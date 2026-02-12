import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.core.middleware import JWTValidationMiddleware
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.core.redis import close_redis, init_redis
from app.routers import (
    analytics,
    companions,
    credits,
    essence,
    health,
    messages,
    moderation,
    partners,
    reflections,
    room,
    schedules,
    sessions,
    users,
    webhooks,
)

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    setup_logging()
    logger.info("Starting %s...", settings.app_name)
    await init_redis()
    logger.info("Redis connection initialized")
    yield
    logger.info("Shutting down %s...", settings.app_name)
    await close_redis()
    logger.info("Redis connection closed")


app = FastAPI(
    title=settings.app_name,
    description="Body doubling platform API for Focus Squad",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT validation middleware (runs after CORS, before routes)
app.add_middleware(JWTValidationMiddleware)

# Rate limiting (slowapi + Redis)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Global exception handlers (domain exceptions → HTTP responses)
register_exception_handlers(app)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(users.router, prefix=f"{settings.api_prefix}/users", tags=["Users"])
# Reflections router first: static /diary must be matched before /{session_id}
app.include_router(
    reflections.router, prefix=f"{settings.api_prefix}/sessions", tags=["Reflections"]
)
app.include_router(sessions.router, prefix=f"{settings.api_prefix}/sessions", tags=["Sessions"])
app.include_router(credits.router, prefix=f"{settings.api_prefix}/credits", tags=["Credits"])
app.include_router(analytics.router, prefix=f"{settings.api_prefix}/analytics", tags=["Analytics"])
app.include_router(
    moderation.router, prefix=f"{settings.api_prefix}/moderation", tags=["Moderation"]
)
app.include_router(partners.router, prefix=f"{settings.api_prefix}/partners", tags=["Partners"])
app.include_router(messages.router, prefix=f"{settings.api_prefix}/messages", tags=["Messages"])
app.include_router(schedules.router, prefix=f"{settings.api_prefix}/schedules", tags=["Schedules"])
app.include_router(essence.router, prefix=f"{settings.api_prefix}/essence", tags=["Essence"])
app.include_router(room.router, prefix=f"{settings.api_prefix}/room", tags=["Room"])
app.include_router(
    companions.router, prefix=f"{settings.api_prefix}/companions", tags=["Companions"]
)
app.include_router(webhooks.router, prefix=f"{settings.api_prefix}/webhooks", tags=["Webhooks"])
