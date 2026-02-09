"""Tests for centralized logging configuration."""

import json
import logging
import sys
from unittest.mock import MagicMock, patch

from app.core.logging_config import JSONFormatter, setup_logging


class TestJSONFormatter:
    def test_formats_as_json(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = json.loads(formatter.format(record))
        assert result["message"] == "Test message"
        assert result["level"] == "INFO"
        assert result["logger"] == "test.logger"
        assert "timestamp" in result

    def test_includes_exception_info(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
        result = json.loads(formatter.format(record))
        assert "exception" in result
        assert "ValueError" in result["exception"]

    def test_excludes_exception_when_none(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="No error",
            args=(),
            exc_info=None,
        )
        result = json.loads(formatter.format(record))
        assert "exception" not in result

    def test_includes_extra_fields(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="With extras",
            args=(),
            exc_info=None,
        )
        record.user_id = "user-123"
        record.path = "/api/v1/test"
        result = json.loads(formatter.format(record))
        assert result["user_id"] == "user-123"
        assert result["path"] == "/api/v1/test"


class TestSetupLogging:
    def teardown_method(self):
        """Reset root logger after each test."""
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.WARNING)

    @patch("app.core.logging_config.get_settings")
    def test_debug_mode_uses_readable_format(self, mock_settings):
        mock_settings.return_value = MagicMock(debug=True)
        setup_logging()
        root = logging.getLogger()
        assert len(root.handlers) >= 1
        assert not isinstance(root.handlers[0].formatter, JSONFormatter)

    @patch("app.core.logging_config.get_settings")
    def test_production_mode_uses_json(self, mock_settings):
        mock_settings.return_value = MagicMock(debug=False)
        setup_logging()
        root = logging.getLogger()
        assert isinstance(root.handlers[0].formatter, JSONFormatter)

    @patch("app.core.logging_config.get_settings")
    def test_level_override(self, mock_settings):
        mock_settings.return_value = MagicMock(debug=False)
        setup_logging(level="WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    @patch("app.core.logging_config.get_settings")
    def test_quiets_noisy_loggers(self, mock_settings):
        mock_settings.return_value = MagicMock(debug=False)
        setup_logging()
        assert logging.getLogger("uvicorn.access").level == logging.WARNING
        assert logging.getLogger("httpx").level == logging.WARNING
