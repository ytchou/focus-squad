"""
Centralized logging configuration for Focus Squad API.

Structured JSON in production, human-readable in development.
Call setup_logging() once at app startup (in lifespan).
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from app.core.config import get_settings


class CorrelationIDFilter(logging.Filter):
    """
    Logging filter that injects correlation ID into all log records.

    The correlation ID is retrieved from the ContextVar set by
    CorrelationIDMiddleware, allowing all log messages within a
    request to share the same ID for tracing.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Import here to avoid circular imports
        from app.core.middleware import get_correlation_id

        record.correlation_id = get_correlation_id() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Include correlation_id from filter
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id and correlation_id != "-":
            log_entry["correlation_id"] = correlation_id
        for key in ("user_id", "request_id", "path", "method", "status_code"):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value
        return json.dumps(log_entry)


def setup_logging(level: Optional[str] = None) -> None:
    """Configure application-wide logging."""
    settings = get_settings()
    log_level = level or ("DEBUG" if settings.debug else "INFO")

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Add correlation ID filter to inject request IDs into all logs
    handler.addFilter(CorrelationIDFilter())

    if settings.debug:
        # Include correlation_id in dev format
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s [%(correlation_id)s]: %(message)s",
            datefmt="%H:%M:%S",
        )
    else:
        formatter = JSONFormatter()

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quiet noisy third-party loggers (uvicorn[standard] pulls in many verbose libs)
    noisy_loggers = [
        "uvicorn.access",
        "httpx",
        "httpcore",
        "hpack",
        "h2",
        "h11",
        "websockets",
        "watchfiles",
        "multipart",
    ]
    for name in noisy_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)
