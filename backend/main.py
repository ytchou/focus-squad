"""Entry point for running the FastAPI application."""

from app.main import app

# Run with: uvicorn main:app --reload

__all__ = ["app"]
