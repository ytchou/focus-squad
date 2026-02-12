-- Migration: 027_atomic_essence_deduction.sql
-- Description: Atomic essence deduction function to prevent race conditions
-- in concurrent purchases. Also adds CHECK constraint to prevent negative balances.

-- Add CHECK constraint as safety net
ALTER TABLE furniture_essence ADD CONSTRAINT furniture_essence_balance_non_negative CHECK (balance >= 0);

-- Atomic essence deduction: deducts balance and increments total_spent in a single
-- UPDATE with WHERE balance >= cost, preventing concurrent purchases from overdrawing.
CREATE OR REPLACE FUNCTION deduct_essence(p_user_id UUID, p_cost INTEGER)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_rows_affected INTEGER;
BEGIN
    UPDATE furniture_essence
    SET balance = balance - p_cost,
        total_spent = total_spent + p_cost,
        updated_at = NOW()
    WHERE user_id = p_user_id
      AND balance >= p_cost;

    GET DIAGNOSTICS v_rows_affected = ROW_COUNT;

    IF v_rows_affected = 0 THEN
        RETURN json_build_object('success', false);
    END IF;

    RETURN json_build_object('success', true);
END;
$$;
