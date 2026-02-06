-- ===========================================
-- FIX PARTICIPANT CONSTRAINTS FOR SEAT/USER REUSE
-- Migration: 006_fix_seat_reuse_constraint.sql
-- ===========================================
-- Problem: UNIQUE constraints on (session_id, seat_number) and
-- (session_id, user_id) prevent reusing seats/rejoining after leaving.
--
-- Solution: Replace with partial unique indexes that only enforce
-- uniqueness for ACTIVE participants (where left_at IS NULL).

-- ===========================================
-- DROP EXISTING CONSTRAINTS
-- ===========================================

-- Drop seat uniqueness constraint
ALTER TABLE session_participants
    DROP CONSTRAINT IF EXISTS session_participants_session_id_seat_number_key;

-- Drop user uniqueness constraint (prevents rejoining after leaving)
ALTER TABLE session_participants
    DROP CONSTRAINT IF EXISTS session_participants_session_id_user_id_key;

-- ===========================================
-- CREATE PARTIAL UNIQUE INDEXES
-- ===========================================

-- Only enforce seat uniqueness for active participants
-- This allows the same seat to be reused after someone leaves
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_participants_active_seat
    ON session_participants(session_id, seat_number)
    WHERE left_at IS NULL;

-- Only enforce user uniqueness for active participants
-- This allows users to rejoin a session after leaving
CREATE UNIQUE INDEX IF NOT EXISTS idx_session_participants_active_user
    ON session_participants(session_id, user_id)
    WHERE left_at IS NULL;

-- ===========================================
-- COMMENTS
-- ===========================================

COMMENT ON INDEX idx_session_participants_active_seat IS
    'Ensures each seat (1-4) is only taken by one ACTIVE participant. Seats can be reused after participant leaves.';

COMMENT ON INDEX idx_session_participants_active_user IS
    'Ensures each user can only be in a session once while ACTIVE. Users can rejoin after leaving.';
