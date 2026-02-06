-- ===========================================
-- LIVEKIT CONNECTION TRACKING
-- Migration: 004_livekit_connection_tracking.sql
-- ===========================================
-- Adds columns to track LiveKit connection state for participants and rooms.
-- Used by webhook handlers to update connection status in real-time.

-- ===========================================
-- SESSION PARTICIPANTS: Connection tracking
-- ===========================================

-- Track when participant connected to LiveKit room
ALTER TABLE session_participants
    ADD COLUMN IF NOT EXISTS connected_at TIMESTAMPTZ;

-- Track when participant disconnected (may reconnect within grace period)
ALTER TABLE session_participants
    ADD COLUMN IF NOT EXISTS disconnected_at TIMESTAMPTZ;

-- Current connection status (updated by webhooks)
ALTER TABLE session_participants
    ADD COLUMN IF NOT EXISTS is_connected BOOLEAN DEFAULT false;

-- ===========================================
-- SESSIONS: Room lifecycle tracking
-- ===========================================

-- Track when LiveKit room was created (by scheduled task)
ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS livekit_room_created_at TIMESTAMPTZ;

-- Track when LiveKit room was deleted (by cleanup task)
ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS livekit_room_deleted_at TIMESTAMPTZ;

-- ===========================================
-- INDEXES
-- ===========================================

-- Index for finding connected participants (useful for health checks)
CREATE INDEX IF NOT EXISTS idx_session_participants_connected
    ON session_participants(session_id, is_connected)
    WHERE is_connected = true;

-- ===========================================
-- COMMENTS
-- ===========================================

COMMENT ON COLUMN session_participants.connected_at IS 'Timestamp when participant first connected to LiveKit room';
COMMENT ON COLUMN session_participants.disconnected_at IS 'Timestamp of most recent disconnection from LiveKit room';
COMMENT ON COLUMN session_participants.is_connected IS 'Current LiveKit connection status, updated by webhooks';
COMMENT ON COLUMN sessions.livekit_room_created_at IS 'Timestamp when LiveKit room was explicitly created via API';
COMMENT ON COLUMN sessions.livekit_room_deleted_at IS 'Timestamp when LiveKit room was deleted after session end';
