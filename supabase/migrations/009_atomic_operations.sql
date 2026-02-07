-- ===========================================
-- ATOMIC OPERATIONS & IDEMPOTENCY
-- Migration: 009_atomic_operations.sql
-- ===========================================
-- Adds PostgreSQL RPC functions for atomic operations and idempotency support.
-- Prevents race conditions in concurrent joins and credit transfers.

-- ===========================================
-- IDEMPOTENCY SUPPORT
-- ===========================================

ALTER TABLE credit_transactions
    ADD COLUMN IF NOT EXISTS idempotency_key UUID;

CREATE UNIQUE INDEX IF NOT EXISTS idx_credit_transactions_idempotency
    ON credit_transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;

COMMENT ON COLUMN credit_transactions.idempotency_key IS 'Optional dedup key to prevent double-processing from duplicate webhook calls';

-- ===========================================
-- RPC: atomic_add_participant
-- ===========================================
-- Atomically adds a participant to a session with:
-- - Phase lock (setup only)
-- - Row-level locking to serialize concurrent joins
-- - Idempotent handling (already active → return existing)
-- - Seat reuse for returning participants
--
-- Returns: participant_id, seat_number, already_active

CREATE OR REPLACE FUNCTION atomic_add_participant(
    p_session_id UUID,
    p_user_id UUID
)
RETURNS TABLE(participant_id UUID, seat_number INT, already_active BOOLEAN)
LANGUAGE plpgsql
AS $$
DECLARE
    v_phase session_phase;
    v_existing RECORD;
    v_taken_seats INT[];
    v_available_seat INT;
    v_inactive RECORD;
    v_new_id UUID;
BEGIN
    -- 1. Phase lock: only allow joins during setup
    SELECT current_phase INTO v_phase
    FROM sessions
    WHERE id = p_session_id
    FOR UPDATE;

    IF v_phase IS NULL THEN
        RAISE EXCEPTION 'SESSION_NOT_FOUND: Session % not found', p_session_id;
    END IF;

    IF v_phase != 'setup' THEN
        RAISE EXCEPTION 'SESSION_PHASE_ERROR: Cannot join session in % phase, must be setup', v_phase;
    END IF;

    -- 2. Check if user is already active (idempotent)
    SELECT sp.id, sp.seat_number INTO v_existing
    FROM session_participants sp
    WHERE sp.session_id = p_session_id
      AND sp.user_id = p_user_id
      AND sp.left_at IS NULL
    FOR UPDATE;

    IF FOUND THEN
        RETURN QUERY SELECT v_existing.id, v_existing.seat_number, TRUE;
        RETURN;
    END IF;

    -- 3. Lock active participants and check capacity
    SELECT array_agg(sp.seat_number) INTO v_taken_seats
    FROM session_participants sp
    WHERE sp.session_id = p_session_id
      AND sp.left_at IS NULL
    FOR UPDATE;

    v_taken_seats := COALESCE(v_taken_seats, ARRAY[]::INT[]);

    IF array_length(v_taken_seats, 1) >= 4 THEN
        RAISE EXCEPTION 'SESSION_FULL: Session % is full (4/4 seats taken)', p_session_id;
    END IF;

    -- Find first available seat (1-4)
    SELECT s INTO v_available_seat
    FROM unnest(ARRAY[1,2,3,4]) AS s
    WHERE s != ALL(v_taken_seats)
    ORDER BY s
    LIMIT 1;

    -- 4. Check for inactive (previously left) record to reactivate
    SELECT sp.id INTO v_inactive
    FROM session_participants sp
    WHERE sp.session_id = p_session_id
      AND sp.user_id = p_user_id
      AND sp.left_at IS NOT NULL
    LIMIT 1;

    IF FOUND THEN
        UPDATE session_participants
        SET left_at = NULL,
            seat_number = v_available_seat,
            joined_at = NOW()
        WHERE id = v_inactive.id;

        RETURN QUERY SELECT v_inactive.id, v_available_seat, FALSE;
        RETURN;
    END IF;

    -- 5. Insert new participant
    INSERT INTO session_participants (session_id, user_id, participant_type, seat_number)
    VALUES (p_session_id, p_user_id, 'human', v_available_seat)
    RETURNING id INTO v_new_id;

    RETURN QUERY SELECT v_new_id, v_available_seat, FALSE;
END;
$$;

COMMENT ON FUNCTION atomic_add_participant IS 'Atomically add a participant with phase lock, capacity check, and seat assignment';

-- ===========================================
-- RPC: atomic_transfer_credits
-- ===========================================
-- Atomically transfers credits between two users.
-- Python validates business rules (tier, limits) beforehand.
-- SQL handles the money movement atomically.
--
-- Returns: sender_new_balance, recipient_new_balance

CREATE OR REPLACE FUNCTION atomic_transfer_credits(
    p_sender_id UUID,
    p_recipient_id UUID,
    p_amount INT,
    p_idempotency_key UUID DEFAULT NULL
)
RETURNS TABLE(sender_new_balance INT, recipient_new_balance INT)
LANGUAGE plpgsql
AS $$
DECLARE
    v_sender_balance INT;
    v_recipient_balance INT;
    v_existing RECORD;
BEGIN
    -- 1. Check idempotency key (return early if duplicate)
    IF p_idempotency_key IS NOT NULL THEN
        SELECT ct.id INTO v_existing
        FROM credit_transactions ct
        WHERE ct.idempotency_key = p_idempotency_key
        LIMIT 1;

        IF FOUND THEN
            -- Already processed, return current balances
            SELECT c.credits_remaining INTO v_sender_balance
            FROM credits c WHERE c.user_id = p_sender_id;

            SELECT c.credits_remaining INTO v_recipient_balance
            FROM credits c WHERE c.user_id = p_recipient_id;

            RETURN QUERY SELECT v_sender_balance, v_recipient_balance;
            RETURN;
        END IF;
    END IF;

    -- 2. Lock sender row and verify balance
    SELECT c.credits_remaining INTO v_sender_balance
    FROM credits c
    WHERE c.user_id = p_sender_id
    FOR UPDATE;

    IF v_sender_balance IS NULL THEN
        RAISE EXCEPTION 'SENDER_NOT_FOUND: Sender % not found', p_sender_id;
    END IF;

    IF v_sender_balance < p_amount THEN
        RAISE EXCEPTION 'INSUFFICIENT_CREDITS: Sender has % credits, needs %', v_sender_balance, p_amount;
    END IF;

    -- 3. Deduct from sender
    UPDATE credits
    SET credits_remaining = credits_remaining - p_amount,
        updated_at = NOW()
    WHERE user_id = p_sender_id;

    v_sender_balance := v_sender_balance - p_amount;

    -- 4. Add to recipient
    UPDATE credits
    SET credits_remaining = credits_remaining + p_amount,
        updated_at = NOW()
    WHERE user_id = p_recipient_id;

    SELECT c.credits_remaining INTO v_recipient_balance
    FROM credits c WHERE c.user_id = p_recipient_id;

    -- 5. Log both transactions
    INSERT INTO credit_transactions (user_id, amount, transaction_type, description, related_user_id, idempotency_key)
    VALUES (p_sender_id, -p_amount, 'gift_sent', 'Gift to ' || p_recipient_id, p_recipient_id, p_idempotency_key);

    INSERT INTO credit_transactions (user_id, amount, transaction_type, description, related_user_id)
    VALUES (p_recipient_id, p_amount, 'gift_received', 'Gift from ' || p_sender_id, p_sender_id);

    RETURN QUERY SELECT v_sender_balance, v_recipient_balance;
END;
$$;

COMMENT ON FUNCTION atomic_transfer_credits IS 'Atomically transfer credits between users with idempotency support';
