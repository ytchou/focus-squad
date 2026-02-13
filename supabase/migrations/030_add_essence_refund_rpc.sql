-- Migration: 030_add_essence_refund_rpc.sql
-- Description: Atomic essence refund function for compensating transactions
-- when inventory inserts fail after essence has been deducted.

CREATE OR REPLACE FUNCTION add_essence(p_user_id UUID, p_amount INTEGER)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows_affected INTEGER;
BEGIN
    UPDATE furniture_essence
    SET balance = balance + p_amount,
        total_spent = total_spent - p_amount,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    GET DIAGNOSTICS v_rows_affected = ROW_COUNT;

    IF v_rows_affected = 0 THEN
        RETURN json_build_object('success', false);
    END IF;

    RETURN json_build_object('success', true);
END;
$$;
