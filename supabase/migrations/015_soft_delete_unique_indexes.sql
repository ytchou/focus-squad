-- Phase 3D fix: Partial unique indexes for soft-delete
-- Ensures uniqueness only among active (non-deleted) users,
-- allowing re-registration after account purge.
-- Follows same pattern as 006_fix_seat_reuse_constraint.sql.

-- Drop inline UNIQUE constraints
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_auth_id_key;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_username_key;

-- Replace with partial unique indexes (active accounts only)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_active_auth_id
    ON users(auth_id) WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_active_email
    ON users(email) WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_active_username
    ON users(username) WHERE deleted_at IS NULL;
