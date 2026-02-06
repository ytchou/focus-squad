-- ===========================================
-- ADD USER STATS INCREMENT FUNCTION
-- Migration: 007_add_user_stats_increment_function.sql
-- ===========================================
-- Provides atomic increment for user session stats.
-- Used after session completion to update session_count and total_focus_minutes.

CREATE OR REPLACE FUNCTION increment_user_stats(
    p_user_id UUID,
    p_focus_minutes INTEGER
)
RETURNS VOID AS $$
BEGIN
    UPDATE users
    SET
        session_count = session_count + 1,
        total_focus_minutes = total_focus_minutes + p_focus_minutes,
        updated_at = NOW()
    WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION increment_user_stats TO authenticated;

COMMENT ON FUNCTION increment_user_stats IS
    'Atomically increments session_count by 1 and adds focus_minutes to total. Used after session completion.';
