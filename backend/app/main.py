from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.middleware import JWTValidationMiddleware
from app.core.redis import close_redis, init_redis
from app.routers import credits, health, sessions, users

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"Starting {settings.app_name}...")
    await init_redis()
    print("Redis connection initialized")
    yield
    # Shutdown
    print(f"Shutting down {settings.app_name}...")
    await close_redis()
    print("Redis connection closed")


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

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(users.router, prefix=f"{settings.api_prefix}/users", tags=["Users"])
app.include_router(sessions.router, prefix=f"{settings.api_prefix}/sessions", tags=["Sessions"])
app.include_router(credits.router, prefix=f"{settings.api_prefix}/credits", tags=["Credits"])
