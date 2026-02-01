-- Focus Squad Schema Enhancement: User Service Tables
-- Migration 002: Add notification preferences, essence transactions, and performance indexes

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- NOTIFICATION PREFERENCES TABLE
-- ===========================================

CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Event type (e.g., 'session_start', 'match_found', 'credit_refresh', 'red_rating')
    event_type TEXT NOT NULL,

    -- Channel preferences
    email_enabled BOOLEAN DEFAULT true,
    push_enabled BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- One preference row per user per event type
    UNIQUE(user_id, event_type)
);

CREATE INDEX idx_notification_preferences_user ON notification_preferences(user_id);

-- Auto-update updated_at timestamp
CREATE TRIGGER notification_preferences_updated_at
    BEFORE UPDATE ON notification_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ===========================================
-- ESSENCE TRANSACTIONS TABLE
-- ===========================================

CREATE TABLE essence_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    amount INTEGER NOT NULL, -- positive = earned, negative = spent
    transaction_type TEXT NOT NULL, -- 'session_complete', 'item_purchase', 'streak_bonus', 'admin_adjustment'
    description TEXT,

    -- Link to session if earned from completing a session
    related_session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,

    -- Link to item if spent on purchasing an item
    related_item_id UUID REFERENCES items(id) ON DELETE SET NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_essence_transactions_user ON essence_transactions(user_id);
CREATE INDEX idx_essence_transactions_session ON essence_transactions(related_session_id);
CREATE INDEX idx_essence_transactions_created ON essence_transactions(created_at);

-- ===========================================
-- PERFORMANCE INDEXES (Missing from 001)
-- ===========================================

-- Critical for auth mapping (auth_id -> user lookup)
CREATE INDEX idx_users_auth_id ON users(auth_id);

-- For credit transaction history queries
CREATE INDEX idx_credit_transactions_user ON credit_transactions(user_id);

-- For time-decay weighted rating queries
CREATE INDEX idx_ratings_created ON ratings(created_at);

-- ===========================================
-- ROW LEVEL SECURITY (RLS)
-- ===========================================

ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE essence_transactions ENABLE ROW LEVEL SECURITY;

-- Users can only view and manage their own notification preferences
CREATE POLICY "Users can view own notification preferences" ON notification_preferences
    FOR SELECT USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

CREATE POLICY "Users can update own notification preferences" ON notification_preferences
    FOR UPDATE USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

CREATE POLICY "Users can insert own notification preferences" ON notification_preferences
    FOR INSERT WITH CHECK (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

-- Users can only view their own essence transactions
CREATE POLICY "Users can view own essence transactions" ON essence_transactions
    FOR SELECT USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

-- Note: Essence transactions are created by the backend service, not directly by users
-- INSERT policy is intentionally omitted (backend uses service role)
