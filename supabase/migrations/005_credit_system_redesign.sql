-- ===========================================
-- CREDIT SYSTEM REDESIGN
-- Migration: 005_credit_system_redesign.sql
-- ===========================================
-- Implements rolling 7-day refresh (per-user) and cancel/refund tracking.
-- Design doc: output/plan/2025-02-06-credit-system-redesign.md

-- ===========================================
-- CREDITS TABLE: Rolling refresh support
-- ===========================================

-- Add rolling cycle start date (replaces fixed weekly refresh)
-- Initialized to user's signup date or current date for existing users
ALTER TABLE credits
    ADD COLUMN IF NOT EXISTS credit_cycle_start DATE DEFAULT CURRENT_DATE;

-- Migrate existing data: copy week_start_date to credit_cycle_start
UPDATE credits
SET credit_cycle_start = COALESCE(week_start_date, CURRENT_DATE)
WHERE credit_cycle_start IS NULL OR credit_cycle_start = CURRENT_DATE;

-- Drop obsolete columns (no longer needed with rolling refresh)
ALTER TABLE credits DROP COLUMN IF EXISTS week_start_date;
ALTER TABLE credits DROP COLUMN IF EXISTS credits_used_this_week;

-- ===========================================
-- SESSION PARTICIPANTS: Credit/refund tracking
-- ===========================================

-- Track when credit was deducted for this booking
ALTER TABLE session_participants
    ADD COLUMN IF NOT EXISTS credit_deducted_at TIMESTAMPTZ;

-- Track when credit was refunded (NULL = not refunded, prevents double-refund)
ALTER TABLE session_participants
    ADD COLUMN IF NOT EXISTS credit_refunded_at TIMESTAMPTZ;

-- Link to the credit transaction record for audit trail
ALTER TABLE session_participants
    ADD COLUMN IF NOT EXISTS credit_transaction_id UUID REFERENCES credit_transactions(id);

-- ===========================================
-- INDEXES
-- ===========================================

-- Index for finding users due for credit refresh (daily Celery task)
CREATE INDEX IF NOT EXISTS idx_credits_cycle_start
    ON credits(credit_cycle_start);

-- Index for finding bookings eligible for refund
CREATE INDEX IF NOT EXISTS idx_session_participants_credit_refund
    ON session_participants(credit_deducted_at)
    WHERE credit_refunded_at IS NULL;

-- ===========================================
-- COMMENTS
-- ===========================================

COMMENT ON COLUMN credits.credit_cycle_start IS 'Start of users rolling 7-day credit cycle. Refresh happens when current_date >= credit_cycle_start + 7';
COMMENT ON COLUMN session_participants.credit_deducted_at IS 'When credit was deducted for this booking';
COMMENT ON COLUMN session_participants.credit_refunded_at IS 'When credit was refunded (if cancelled >=1hr before). NULL means not refunded.';
COMMENT ON COLUMN session_participants.credit_transaction_id IS 'FK to credit_transactions for audit trail';
