from fastapi import APIRouter

from app.core.redis import get_redis

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "focus-squad-api"}


@router.get("/health/redis")
async def redis_health_check():
    """Redis health check endpoint."""
    try:
        redis = get_redis()
        await redis.ping()
        return {"status": "healthy", "service": "redis"}
    except Exception as e:
        return {"status": "unhealthy", "service": "redis", "error": str(e)}


@router.get("/health/livekit")
async def livekit_health_check():
    """LiveKit configuration health check."""
    from app.services.livekit_service import LiveKitService

    service = LiveKitService()
    if service.is_configured:
        return {
            "status": "configured",
            "service": "livekit",
            "message": "LiveKit credentials are set. Ready for live audio!",
        }
    else:
        return {
            "status": "not_configured",
            "service": "livekit",
            "message": "LiveKit credentials missing. Set LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL in backend/.env",
        }


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Focus Squad API", "docs": "/docs"}
