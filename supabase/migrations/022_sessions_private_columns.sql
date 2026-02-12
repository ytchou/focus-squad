-- Add private session support columns to sessions table
ALTER TABLE sessions ADD COLUMN is_private BOOLEAN DEFAULT FALSE;
ALTER TABLE sessions ADD COLUMN created_by UUID REFERENCES users(id);
ALTER TABLE sessions ADD COLUMN recurring_schedule_id UUID REFERENCES recurring_schedules(id);
ALTER TABLE sessions ADD COLUMN max_seats INTEGER DEFAULT 4
    CHECK (max_seats BETWEEN 2 AND 4);

-- Index for excluding private sessions from public matching
CREATE INDEX idx_sessions_is_private ON sessions(is_private);

-- Backfill: all existing sessions are public
UPDATE sessions SET is_private = FALSE WHERE is_private IS NULL;
