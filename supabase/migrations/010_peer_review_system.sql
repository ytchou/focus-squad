-- Peer Review System
-- Adds rating reasons, pending_ratings table, and supporting indexes
-- Design: output/plan/2026-02-08-peer-review-system.md

-- ===========================================
-- EXTEND RATINGS TABLE
-- ===========================================

-- Add structured reason data for "red" ratings
-- Stores: {"reasons": ["absent_no_show", "disruptive_behavior"], "other_text": "..."}
ALTER TABLE ratings ADD COLUMN reason JSONB DEFAULT NULL;

-- Composite index for reliability score calculation (180-day horizon queries)
CREATE INDEX IF NOT EXISTS idx_ratings_ratee_created ON ratings(ratee_id, created_at);

-- ===========================================
-- PENDING RATINGS TABLE
-- ===========================================

-- Tracks which sessions a user needs to rate before joining the next one.
-- Separate table for fast O(1) lookup on session-join blocker.
CREATE TABLE pending_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Human tablemate IDs that need rating
    rateable_user_ids UUID[] NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,  -- NULL until submitted or skipped
    expires_at TIMESTAMPTZ NOT NULL,  -- created_at + 48 hours

    UNIQUE(user_id, session_id)
);

-- Partial index: only uncompleted pending ratings (used by session-join blocker)
CREATE INDEX idx_pending_ratings_active
    ON pending_ratings(user_id)
    WHERE completed_at IS NULL;

-- ===========================================
-- ROW LEVEL SECURITY
-- ===========================================

ALTER TABLE pending_ratings ENABLE ROW LEVEL SECURITY;

-- Users can read their own pending ratings
CREATE POLICY pending_ratings_select ON pending_ratings
    FOR SELECT USING (user_id = auth.uid());

-- Users can update their own pending ratings (mark as completed)
CREATE POLICY pending_ratings_update ON pending_ratings
    FOR UPDATE USING (user_id = auth.uid());

-- Only service role can insert pending ratings (created by backend)
CREATE POLICY pending_ratings_insert ON pending_ratings
    FOR INSERT WITH CHECK (true);
