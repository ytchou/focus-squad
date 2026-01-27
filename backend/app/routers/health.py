from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "focus-squad-api"}


@router.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Focus Squad API", "docs": "/docs"}
