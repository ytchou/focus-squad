-- Migration: 011_session_reflections
-- Description: Add session_reflections table for structured phase reflections
-- Design doc: output/plan/2026-02-08-session-board-design.md

-- =============================================================================
-- Session Reflections Table
-- =============================================================================
-- Stores structured reflections at phase transitions (setup, break, social).
-- One reflection per user per phase per session (upsert on edit).
-- Free-form chat messages are NOT stored (ephemeral via LiveKit data channels).

CREATE TABLE session_reflections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phase TEXT NOT NULL CHECK (phase IN ('setup', 'break', 'social')),
    content TEXT NOT NULL CHECK (char_length(content) <= 500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (session_id, user_id, phase)
);

-- Index for diary queries (user's reflections ordered by date)
CREATE INDEX idx_reflections_user_date ON session_reflections(user_id, created_at DESC);

-- Index for loading all reflections in a session (late joiner hydration)
CREATE INDEX idx_reflections_session ON session_reflections(session_id);

-- =============================================================================
-- RLS Policies
-- =============================================================================

ALTER TABLE session_reflections ENABLE ROW LEVEL SECURITY;

-- Users can read reflections from sessions they participated in
CREATE POLICY "Users can read reflections from their sessions"
    ON session_reflections FOR SELECT
    USING (
        user_id = auth.uid()
        OR session_id IN (
            SELECT session_id FROM session_participants
            WHERE user_id = auth.uid()
        )
    );

-- Users can insert their own reflections
CREATE POLICY "Users can insert own reflections"
    ON session_reflections FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Users can update their own reflections
CREATE POLICY "Users can update own reflections"
    ON session_reflections FOR UPDATE
    USING (user_id = auth.uid());
