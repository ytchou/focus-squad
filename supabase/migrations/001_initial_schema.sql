-- Focus Squad Initial Database Schema
-- Run this in Supabase SQL Editor or via migrations

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- ENUMS
-- ===========================================

CREATE TYPE user_tier AS ENUM ('free', 'pro', 'elite', 'infinite');
CREATE TYPE table_mode AS ENUM ('forced_audio', 'quiet');
CREATE TYPE session_phase AS ENUM ('setup', 'work_1', 'break', 'work_2', 'social', 'ended');
CREATE TYPE rating_value AS ENUM ('green', 'red', 'skip');
CREATE TYPE participant_type AS ENUM ('human', 'ai_companion');

-- ===========================================
-- USERS TABLE
-- ===========================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- Auth (linked to Supabase Auth)
    auth_id UUID UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,

    -- Profile
    username TEXT UNIQUE NOT NULL,
    display_name TEXT,
    bio TEXT,
    avatar_config JSONB DEFAULT '{}',
    social_links JSONB DEFAULT '{}',
    study_interests TEXT[] DEFAULT '{}',
    preferred_language TEXT DEFAULT 'en' CHECK (preferred_language IN ('en', 'zh-TW')),

    -- Stats
    reliability_score DECIMAL(5,2) DEFAULT 100.00 CHECK (reliability_score >= 0 AND reliability_score <= 100),
    total_focus_minutes INTEGER DEFAULT 0,
    session_count INTEGER DEFAULT 0,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_session_date DATE,

    -- Settings
    activity_tracking_enabled BOOLEAN DEFAULT false,
    email_notifications_enabled BOOLEAN DEFAULT true,
    push_notifications_enabled BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    banned_until TIMESTAMPTZ
);

-- ===========================================
-- CREDITS TABLE
-- ===========================================

CREATE TABLE credits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Tier & Balance
    tier user_tier DEFAULT 'free',
    credits_remaining INTEGER DEFAULT 2,
    credits_used_this_week INTEGER DEFAULT 0,
    gifts_sent_this_week INTEGER DEFAULT 0,

    -- Week tracking (resets weekly)
    week_start_date DATE DEFAULT CURRENT_DATE,

    -- Referral
    referral_code TEXT UNIQUE,
    referred_by UUID REFERENCES users(id),
    referrals_completed INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id)
);

-- ===========================================
-- CREDIT TRANSACTIONS TABLE
-- ===========================================

CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    amount INTEGER NOT NULL, -- positive = earned, negative = spent
    transaction_type TEXT NOT NULL, -- 'session_join', 'gift_sent', 'gift_received', 'referral', 'weekly_refresh', 'penalty'
    description TEXT,

    -- For gifts
    related_user_id UUID REFERENCES users(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- SESSIONS TABLE (Scheduled Tables)
-- ===========================================

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Scheduling
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,

    -- Configuration
    mode table_mode DEFAULT 'forced_audio',
    topic TEXT,
    language TEXT DEFAULT 'en' CHECK (language IN ('en', 'zh-TW')),

    -- State
    current_phase session_phase DEFAULT 'setup',
    phase_started_at TIMESTAMPTZ,

    -- LiveKit
    livekit_room_name TEXT UNIQUE,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for finding upcoming sessions
CREATE INDEX idx_sessions_start_time ON sessions(start_time);
CREATE INDEX idx_sessions_phase ON sessions(current_phase);

-- ===========================================
-- SESSION PARTICIPANTS TABLE
-- ===========================================

CREATE TABLE session_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- NULL for AI companions

    participant_type participant_type DEFAULT 'human',
    seat_number INTEGER NOT NULL CHECK (seat_number >= 1 AND seat_number <= 4),

    -- For AI companions
    ai_companion_name TEXT,
    ai_companion_avatar JSONB,

    -- Participation tracking
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    left_at TIMESTAMPTZ,
    disconnect_count INTEGER DEFAULT 0,
    total_active_minutes INTEGER DEFAULT 0,

    -- Earnings
    essence_earned BOOLEAN DEFAULT false,

    UNIQUE(session_id, seat_number),
    UNIQUE(session_id, user_id)
);

CREATE INDEX idx_session_participants_session ON session_participants(session_id);
CREATE INDEX idx_session_participants_user ON session_participants(user_id);

-- ===========================================
-- RATINGS TABLE (Peer Reviews)
-- ===========================================

CREATE TABLE ratings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Who rated whom
    rater_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ratee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    rating rating_value NOT NULL,

    -- Weight based on rater's reliability
    rater_reliability_at_time DECIMAL(5,2),
    weight DECIMAL(5,4) DEFAULT 1.0,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- One rating per rater-ratee pair per session
    UNIQUE(session_id, rater_id, ratee_id)
);

CREATE INDEX idx_ratings_ratee ON ratings(ratee_id);
CREATE INDEX idx_ratings_session ON ratings(session_id);

-- ===========================================
-- ITEMS TABLE (Furniture/Collectibles)
-- ===========================================

CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    name TEXT NOT NULL,
    name_zh TEXT, -- Traditional Chinese name
    description TEXT,
    description_zh TEXT,

    category TEXT NOT NULL, -- 'furniture', 'decoration', 'accessory'
    rarity TEXT DEFAULT 'common', -- 'common', 'rare', 'limited'

    -- Visual
    image_url TEXT,
    preview_config JSONB DEFAULT '{}',

    -- Availability
    is_purchasable BOOLEAN DEFAULT true,
    essence_cost INTEGER,
    tier_required user_tier,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================
-- USER ITEMS TABLE (Owned Items)
-- ===========================================

CREATE TABLE user_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,

    acquired_at TIMESTAMPTZ DEFAULT NOW(),
    acquisition_type TEXT DEFAULT 'earned', -- 'earned', 'purchased', 'gift'

    UNIQUE(user_id, item_id)
);

CREATE INDEX idx_user_items_user ON user_items(user_id);

-- ===========================================
-- FURNITURE ESSENCE TABLE
-- ===========================================

CREATE TABLE furniture_essence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    balance INTEGER DEFAULT 0,
    total_earned INTEGER DEFAULT 0,
    total_spent INTEGER DEFAULT 0,

    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id)
);

-- ===========================================
-- REPORTS TABLE (Moderation)
-- ===========================================

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reported_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,

    category TEXT NOT NULL, -- 'harassment', 'inappropriate', 'no_show', 'other'
    description TEXT,

    -- Review status
    status TEXT DEFAULT 'pending', -- 'pending', 'reviewed', 'action_taken', 'dismissed'
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reports_status ON reports(status);

-- ===========================================
-- CHAT MESSAGES TABLE (for keyword filtering/logging)
-- ===========================================

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    content TEXT NOT NULL,
    is_flagged BOOLEAN DEFAULT false,
    flagged_reason TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_flagged ON chat_messages(is_flagged) WHERE is_flagged = true;

-- ===========================================
-- ANALYTICS EVENTS TABLE
-- ===========================================

CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    event_name TEXT NOT NULL,
    event_properties JSONB DEFAULT '{}',

    -- Context
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    device_info JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analytics_events_name ON analytics_events(event_name);
CREATE INDEX idx_analytics_events_user ON analytics_events(user_id);
CREATE INDEX idx_analytics_events_created ON analytics_events(created_at);

-- ===========================================
-- FUNCTIONS & TRIGGERS
-- ===========================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER credits_updated_at
    BEFORE UPDATE ON credits
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Generate unique referral code for new users
CREATE OR REPLACE FUNCTION generate_referral_code()
RETURNS TRIGGER AS $$
BEGIN
    NEW.referral_code = UPPER(SUBSTRING(MD5(NEW.user_id::TEXT || NOW()::TEXT) FROM 1 FOR 8));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER credits_generate_referral
    BEFORE INSERT ON credits
    FOR EACH ROW EXECUTE FUNCTION generate_referral_code();

-- ===========================================
-- ROW LEVEL SECURITY (RLS)
-- ===========================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE credits ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE furniture_essence ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Users can read their own data, public profiles are readable by all
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid() = auth_id);

CREATE POLICY "Public profiles are viewable" ON users
    FOR SELECT USING (true);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid() = auth_id);

-- Credits - users can only see their own
CREATE POLICY "Users can view own credits" ON credits
    FOR SELECT USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

-- Sessions - participants can view
CREATE POLICY "Session participants can view session" ON sessions
    FOR SELECT USING (
        id IN (
            SELECT session_id FROM session_participants
            WHERE user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        )
    );

-- Allow service role full access (for backend)
-- Note: Service role bypasses RLS by default in Supabase
