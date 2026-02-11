-- ===========================================
-- ATOMIC OPERATIONS & IDEMPOTENCY
-- Migration: 009_atomic_operations.sql
-- ===========================================
-- Adds idempotency support for credit transactions.

-- ===========================================
-- IDEMPOTENCY SUPPORT
-- ===========================================

ALTER TABLE credit_transactions
    ADD COLUMN IF NOT EXISTS idempotency_key UUID;

CREATE UNIQUE INDEX IF NOT EXISTS idx_credit_transactions_idempotency
    ON credit_transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;

COMMENT ON COLUMN credit_transactions.idempotency_key IS 'Optional dedup key to prevent double-processing from duplicate webhook calls';
