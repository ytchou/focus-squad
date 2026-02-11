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
