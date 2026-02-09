-- Migration: 012_diary_notes
-- Description: Add diary_notes table for post-session journal entries and tags
-- Related: Session Diary feature (output/plan/2026-02-09-session-diary-design.md)

-- =============================================================================
-- Table: diary_notes
-- =============================================================================

CREATE TABLE diary_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    note TEXT CHECK (char_length(note) <= 2000),
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_diary_notes_session_user UNIQUE (session_id, user_id)
);

-- Indexes
CREATE INDEX idx_diary_notes_user ON diary_notes(user_id);
CREATE INDEX idx_diary_notes_session ON diary_notes(session_id);
CREATE INDEX idx_diary_notes_tags ON diary_notes USING GIN(tags);

-- =============================================================================
-- Row Level Security
-- =============================================================================

ALTER TABLE diary_notes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own diary notes"
    ON diary_notes FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert own diary notes"
    ON diary_notes FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own diary notes"
    ON diary_notes FOR UPDATE
    USING (user_id = auth.uid());
