-- ===========================================
-- RPC: atomic_add_participant (updated)
-- ===========================================
-- Update atomic_add_participant to respect the session's max_seats column
-- instead of hardcoding a limit of 4.
-- Private tables can have max_seats of 2, 3, or 4.

CREATE OR REPLACE FUNCTION atomic_add_participant(
    p_session_id UUID,
    p_user_id UUID
)
RETURNS TABLE(participant_id UUID, seat_number INT, already_active BOOLEAN)
LANGUAGE plpgsql
AS $$
DECLARE
    v_phase session_phase;
    v_max_seats INT;
    v_existing RECORD;
    v_taken_seats INT[];
    v_available_seat INT;
    v_inactive RECORD;
    v_new_id UUID;
BEGIN
    -- 1. Phase lock: only allow joins during setup
    SELECT current_phase, COALESCE(s.max_seats, 4)
    INTO v_phase, v_max_seats
    FROM sessions s
    WHERE s.id = p_session_id
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

    IF array_length(v_taken_seats, 1) >= v_max_seats THEN
        RAISE EXCEPTION 'SESSION_FULL: Session % is full (%/% seats taken)', p_session_id, array_length(v_taken_seats, 1), v_max_seats;
    END IF;

    -- Find first available seat (1 to max_seats)
    SELECT s INTO v_available_seat
    FROM generate_series(1, v_max_seats) AS s
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
