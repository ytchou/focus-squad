-- Migration: 031_atomic_essence_purchase.sql
-- Purpose: Atomic item purchase/gift RPC that wraps all operations in a single transaction

CREATE OR REPLACE FUNCTION purchase_item_atomic(
    p_user_id UUID,
    p_item_id UUID,
    p_is_gift BOOLEAN DEFAULT FALSE,
    p_recipient_id UUID DEFAULT NULL,
    p_gift_message TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE plpgsql
AS $$
DECLARE
    v_cost INTEGER;
    v_item_name TEXT;
    v_balance INTEGER;
    v_inventory_id UUID;
    v_target_user_id UUID;
BEGIN
    -- 1. Get item cost and name (fail if not found or unavailable)
    SELECT essence_cost, name INTO v_cost, v_item_name
    FROM items
    WHERE id = p_item_id
      AND is_available = TRUE
      AND is_purchasable = TRUE;

    IF v_cost IS NULL THEN
        RETURN json_build_object('success', false, 'error', 'item_not_found');
    END IF;

    -- 2. Lock user's essence row and check balance (prevents concurrent purchases)
    SELECT balance INTO v_balance
    FROM furniture_essence
    WHERE user_id = p_user_id
    FOR UPDATE;

    IF v_balance IS NULL THEN
        RETURN json_build_object('success', false, 'error', 'no_essence_record');
    END IF;

    IF v_balance < v_cost THEN
        RETURN json_build_object('success', false, 'error', 'insufficient_essence');
    END IF;

    -- 3. Deduct essence from buyer
    UPDATE furniture_essence
    SET balance = balance - v_cost,
        total_spent = total_spent + v_cost,
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- 4. Determine target user for inventory
    v_target_user_id := COALESCE(p_recipient_id, p_user_id);

    -- 5. Insert inventory item
    INSERT INTO user_items (user_id, item_id, acquisition_type, gifted_by, gift_message)
    VALUES (
        v_target_user_id,
        p_item_id,
        CASE WHEN p_is_gift THEN 'gift' ELSE 'purchased' END,
        CASE WHEN p_is_gift THEN p_user_id ELSE NULL END,
        CASE WHEN p_is_gift THEN p_gift_message ELSE NULL END
    )
    RETURNING id INTO v_inventory_id;

    -- 6. Log transaction
    INSERT INTO essence_transactions (user_id, amount, transaction_type, description, related_item_id)
    VALUES (
        p_user_id,
        -v_cost,
        CASE WHEN p_is_gift THEN 'item_gift' ELSE 'item_purchase' END,
        CASE WHEN p_is_gift
            THEN 'Gifted ' || v_item_name
            ELSE 'Purchased ' || v_item_name
        END,
        p_item_id
    );

    RETURN json_build_object(
        'success', true,
        'inventory_id', v_inventory_id,
        'new_balance', v_balance - v_cost,
        'item_name', v_item_name,
        'cost', v_cost
    );
END;
$$;
