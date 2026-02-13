-- Migration: 029_social_gamification.sql
-- Description: Phase 4C — Social Gamification (Room Visits, Item Gifting)
--
-- Changes:
--   1. Add gifted_by, gift_message, gift_seen columns to user_items
--   2. Add partial index for unseen gift notifications
--   3. Add RLS policies for partner room/item/companion viewing

-- ===========================================
-- GIFT TRACKING COLUMNS
-- ===========================================

ALTER TABLE user_items ADD COLUMN IF NOT EXISTS gifted_by UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE user_items ADD COLUMN IF NOT EXISTS gift_message TEXT;
ALTER TABLE user_items ADD COLUMN IF NOT EXISTS gift_seen BOOLEAN DEFAULT false;

-- Partial index: only rows that are actual unseen gifts
CREATE INDEX IF NOT EXISTS idx_user_items_unseen_gifts
    ON user_items(user_id, gift_seen)
    WHERE gifted_by IS NOT NULL AND gift_seen = false;

-- ===========================================
-- RLS: PARTNER ROOM VIEWING (defense-in-depth)
-- ===========================================
-- Backend also validates partnership; RLS prevents data leaks at DB level.

-- Helper subquery pattern: get partner user IDs for the authenticated user
-- Used in all three policies below.

CREATE POLICY "Partners can view partner rooms"
    ON user_room FOR SELECT
    USING (
        user_id = (SELECT id FROM users WHERE auth_id = auth.uid())
        OR user_id IN (
            SELECT CASE
                WHEN requester_id = (SELECT id FROM users WHERE auth_id = auth.uid()) THEN addressee_id
                ELSE requester_id
            END
            FROM partnerships
            WHERE status = 'accepted'
              AND (requester_id = (SELECT id FROM users WHERE auth_id = auth.uid())
                   OR addressee_id = (SELECT id FROM users WHERE auth_id = auth.uid()))
        )
    );

CREATE POLICY "Partners can view partner items"
    ON user_items FOR SELECT
    USING (
        user_id = (SELECT id FROM users WHERE auth_id = auth.uid())
        OR user_id IN (
            SELECT CASE
                WHEN requester_id = (SELECT id FROM users WHERE auth_id = auth.uid()) THEN addressee_id
                ELSE requester_id
            END
            FROM partnerships
            WHERE status = 'accepted'
              AND (requester_id = (SELECT id FROM users WHERE auth_id = auth.uid())
                   OR addressee_id = (SELECT id FROM users WHERE auth_id = auth.uid()))
        )
    );

CREATE POLICY "Partners can view partner companions"
    ON user_companions FOR SELECT
    USING (
        user_id = (SELECT id FROM users WHERE auth_id = auth.uid())
        OR user_id IN (
            SELECT CASE
                WHEN requester_id = (SELECT id FROM users WHERE auth_id = auth.uid()) THEN addressee_id
                ELSE requester_id
            END
            FROM partnerships
            WHERE status = 'accepted'
              AND (requester_id = (SELECT id FROM users WHERE auth_id = auth.uid())
                   OR addressee_id = (SELECT id FROM users WHERE auth_id = auth.uid()))
        )
    );
