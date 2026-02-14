-- Scalability indexes for alpha launch (200-1000+ users)
-- CONCURRENTLY omitted because supabase db push wraps migrations in a transaction.
-- For production with heavy write load, run these manually with CONCURRENTLY outside a transaction.

-- User session history (session_service.get_user_sessions)
CREATE INDEX IF NOT EXISTS idx_session_participants_user_created
  ON session_participants(user_id, created_at DESC);

-- Credit history pagination
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_created
  ON credit_transactions(user_id, created_at DESC);

-- Analytics user timeline
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_created
  ON analytics_events(user_id, created_at DESC);

-- Pending ratings hot path (has_pending_ratings)
CREATE INDEX IF NOT EXISTS idx_pending_ratings_user_active
  ON pending_ratings(user_id, expires_at DESC) WHERE completed_at IS NULL;

-- Active messages (soft-delete aware)
CREATE INDEX IF NOT EXISTS idx_messages_active
  ON messages(conversation_id, created_at DESC) WHERE deleted_at IS NULL;

-- Rating duplicate check
CREATE INDEX IF NOT EXISTS idx_ratings_session_rater
  ON ratings(session_id, rater_id);

-- Session analytics event type queries
CREATE INDEX IF NOT EXISTS idx_session_analytics_event_type
  ON session_analytics_events(event_type, created_at DESC);
