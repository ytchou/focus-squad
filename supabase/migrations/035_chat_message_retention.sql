-- Chat message retention: RPC to delete messages older than 90 days.
-- Called by daily Celery task to keep chat_messages table bounded.

CREATE OR REPLACE FUNCTION delete_old_chat_messages(retention_days integer DEFAULT 90)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
  deleted_count integer;
BEGIN
  DELETE FROM chat_messages
  WHERE created_at < NOW() - (retention_days || ' days')::interval;
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$;
