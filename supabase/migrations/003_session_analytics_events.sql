-- Analytics events table for session behavior tracking
-- Tracks waiting room behavior to understand no-show patterns and user engagement

CREATE TABLE IF NOT EXISTS session_analytics_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL, -- 'waiting_room_entered', 'waiting_room_resumed', 'waiting_room_abandoned', 'session_joined_from_waiting_room'
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX idx_analytics_events_user_id ON session_analytics_events(user_id);
CREATE INDEX idx_analytics_events_session_id ON session_analytics_events(session_id);
CREATE INDEX idx_analytics_events_type ON session_analytics_events(event_type);
CREATE INDEX idx_analytics_events_created_at ON session_analytics_events(created_at DESC);

-- Comments for documentation
COMMENT ON TABLE session_analytics_events IS 'Tracks user behavior in waiting rooms and sessions for analytics';
COMMENT ON COLUMN session_analytics_events.event_type IS 'Event types: waiting_room_entered, waiting_room_resumed, waiting_room_abandoned, session_joined_from_waiting_room';
COMMENT ON COLUMN session_analytics_events.metadata IS 'JSON data like wait_minutes, is_immediate, reason for abandonment';
