-- Phase 4B: Diary Integration (Streak Bonuses, Growth Timeline)
-- Adds weekly session streak tracking and room snapshot milestones.

-- =============================================================================
-- Weekly Streaks (session count per week + bonus flags)
-- =============================================================================

CREATE TABLE weekly_streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    session_count INTEGER DEFAULT 0,
    bonus_3_awarded BOOLEAN DEFAULT false,
    bonus_5_awarded BOOLEAN DEFAULT false,
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, week_start)
);

CREATE INDEX idx_weekly_streaks_user_week ON weekly_streaks(user_id, week_start DESC);

ALTER TABLE weekly_streaks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own streaks" ON weekly_streaks
    FOR SELECT USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

CREATE POLICY "Service role can manage streaks" ON weekly_streaks
    FOR ALL USING (auth.role() = 'service_role');

-- =============================================================================
-- Room Snapshots (growth timeline milestones)
-- =============================================================================

CREATE TABLE room_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    milestone_type TEXT NOT NULL CHECK (milestone_type IN (
        'first_item', 'session_milestone', 'companion_discovered',
        'room_unlocked', 'first_diary', 'diary_streak_7', 'first_breakthrough'
    )),
    image_path TEXT NOT NULL,
    session_count_at INTEGER DEFAULT 0,
    diary_excerpt TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_room_snapshots_user ON room_snapshots(user_id);
CREATE INDEX idx_room_snapshots_user_created ON room_snapshots(user_id, created_at DESC);

ALTER TABLE room_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own snapshots" ON room_snapshots
    FOR SELECT USING (user_id IN (SELECT id FROM users WHERE auth_id = auth.uid()));

CREATE POLICY "Service role can manage snapshots" ON room_snapshots
    FOR ALL USING (auth.role() = 'service_role');

-- =============================================================================
-- Supabase Storage bucket for room snapshot images
-- =============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES ('room-snapshots', 'room-snapshots', true, 2097152)
ON CONFLICT (id) DO NOTHING;

CREATE POLICY "Room snapshots are publicly readable"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'room-snapshots');

CREATE POLICY "Service role can upload snapshots"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'room-snapshots'
        AND auth.role() = 'service_role'
    );
