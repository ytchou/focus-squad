-- Recurring schedules for accountability partners (Unlimited plan only)
CREATE TABLE recurring_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    partner_ids UUID[] NOT NULL,
    label TEXT,
    table_mode TEXT NOT NULL DEFAULT 'forced_audio'
        CHECK (table_mode IN ('forced_audio', 'quiet')),
    max_seats INTEGER NOT NULL DEFAULT 4
        CHECK (max_seats BETWEEN 2 AND 4),
    fill_ai BOOLEAN NOT NULL DEFAULT TRUE,
    topic TEXT,
    days_of_week INTEGER[] NOT NULL,
    slot_time TIME NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'Asia/Taipei',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Validate days_of_week contains values 0-6 only
ALTER TABLE recurring_schedules ADD CONSTRAINT valid_days_of_week
    CHECK (
        array_length(days_of_week, 1) BETWEEN 1 AND 7
    );

-- Validate partner_ids length (1-3 partners, since creator is implicit)
ALTER TABLE recurring_schedules ADD CONSTRAINT valid_partner_count
    CHECK (
        array_length(partner_ids, 1) BETWEEN 1 AND 3
    );

CREATE INDEX idx_recurring_schedules_creator ON recurring_schedules(creator_id);
CREATE INDEX idx_recurring_schedules_active ON recurring_schedules(is_active);

-- Auto-update updated_at
CREATE TRIGGER recurring_schedules_updated_at
    BEFORE UPDATE ON recurring_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- RLS
ALTER TABLE recurring_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Creators can manage own schedules"
    ON recurring_schedules FOR ALL
    USING (
        creator_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "Partners can view schedules they belong to"
    ON recurring_schedules FOR SELECT
    USING (
        (SELECT id FROM users WHERE auth_id = auth.uid()) = ANY(partner_ids)
    );
