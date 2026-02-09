"""Tests for rate limiting configuration."""

from unittest.mock import MagicMock

from fastapi import Request

from app.core.rate_limit import _get_rate_limit_key, rate_limit_exceeded_handler


class TestGetRateLimitKey:
    def test_authenticated_user_returns_auth_key(self):
        request = MagicMock(spec=Request)
        request.state.user = MagicMock()
        request.state.user.auth_id = "user-abc-123"

        key = _get_rate_limit_key(request)
        assert key == "auth:user-abc-123"

    def test_no_user_state_returns_ip_key(self):
        request = MagicMock(spec=Request)
        request.state = MagicMock(spec=[])
        request.client.host = "192.168.1.1"

        key = _get_rate_limit_key(request)
        assert key == "ip:192.168.1.1"

    def test_user_state_none_returns_ip_key(self):
        request = MagicMock(spec=Request)
        request.state.user = None
        request.client.host = "10.0.0.1"

        key = _get_rate_limit_key(request)
        assert key == "ip:10.0.0.1"

    def test_no_client_returns_unknown(self):
        request = MagicMock(spec=Request)
        request.state = MagicMock(spec=[])
        request.client = None

        key = _get_rate_limit_key(request)
        assert key == "ip:unknown"


class TestRateLimitExceededHandler:
    def test_returns_429_with_code(self):
        request = MagicMock(spec=Request)
        exc = MagicMock()

        response = rate_limit_exceeded_handler(request, exc)

        assert response.status_code == 429
        import json

        body = json.loads(response.body)
        assert body["code"] == "RATE_LIMIT_EXCEEDED"
        assert "Rate limit exceeded" in body["detail"]
