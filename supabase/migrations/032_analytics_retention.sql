-- Migration: 032_analytics_retention.sql
-- Purpose: RPC for batch deletion of old analytics events

CREATE OR REPLACE FUNCTION delete_old_analytics(
    cutoff_interval INTERVAL DEFAULT '1 year',
    batch_limit INTEGER DEFAULT 1000
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    -- Use CTE to select IDs first, then delete
    -- This avoids locking the entire table during deletion
    WITH to_delete AS (
        SELECT id
        FROM session_analytics_events
        WHERE created_at < NOW() - cutoff_interval
        ORDER BY created_at ASC  -- Delete oldest first
        LIMIT batch_limit
        FOR UPDATE SKIP LOCKED  -- Skip locked rows to avoid contention
    )
    DELETE FROM session_analytics_events
    WHERE id IN (SELECT id FROM to_delete);

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    RETURN json_build_object('deleted', v_deleted);
END;
$$;

COMMENT ON FUNCTION delete_old_analytics IS
'Batch delete analytics events older than cutoff_interval. Uses FOR UPDATE SKIP LOCKED to avoid contention. Returns count of deleted rows.';
