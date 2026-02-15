"""Tests for PostHog analytics helper."""

from unittest.mock import patch


class TestPostHogCapture:
    """Test posthog capture helper functions."""

    @patch("app.core.posthog._posthog")
    @patch("app.core.posthog._initialized", True)
    def test_capture_sends_event(self, mock_posthog):
        from app.core.posthog import capture

        capture(user_id="user-123", event="test_event", properties={"key": "val"})
        mock_posthog.capture.assert_called_once()
        call_kwargs = mock_posthog.capture.call_args
        assert call_kwargs.kwargs["distinct_id"] == "user-123"
        assert call_kwargs.kwargs["event"] == "test_event"
        assert call_kwargs.kwargs["properties"]["key"] == "val"

    @patch("app.core.posthog._posthog")
    @patch("app.core.posthog._initialized", True)
    def test_capture_with_session_group(self, mock_posthog):
        from app.core.posthog import capture

        capture(user_id="user-123", event="test_event", session_id="session-456")
        call_kwargs = mock_posthog.capture.call_args
        assert call_kwargs.kwargs["groups"] == {"session": "session-456"}
        assert call_kwargs.kwargs["properties"]["session_id"] == "session-456"

    @patch("app.core.posthog._posthog")
    @patch("app.core.posthog._initialized", False)
    def test_capture_noop_when_not_initialized(self, mock_posthog):
        from app.core.posthog import capture

        capture(user_id="user-123", event="test_event")
        mock_posthog.capture.assert_not_called()

    @patch("app.core.posthog._posthog")
    @patch("app.core.posthog._initialized", True)
    def test_capture_swallows_exceptions(self, mock_posthog):
        from app.core.posthog import capture

        mock_posthog.capture.side_effect = Exception("network error")
        # Should not raise
        capture(user_id="user-123", event="test_event")

    @patch("app.core.posthog._posthog")
    @patch("app.core.posthog._initialized", True)
    def test_set_person_properties(self, mock_posthog):
        from app.core.posthog import set_person_properties

        set_person_properties("user-123", {"tier": "pro"})
        call_kwargs = mock_posthog.capture.call_args
        assert call_kwargs.kwargs["event"] == "$set"
        assert call_kwargs.kwargs["properties"]["$set"]["tier"] == "pro"
