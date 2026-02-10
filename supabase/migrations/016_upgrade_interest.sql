-- Track users interested in paid tier upgrades ("Notify Me" button)
CREATE TABLE upgrade_interest (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX idx_upgrade_interest_created ON upgrade_interest(created_at);

ALTER TABLE upgrade_interest ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own interest"
    ON upgrade_interest FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "Users can insert own interest"
    ON upgrade_interest FOR INSERT
    WITH CHECK (user_id = auth.uid());
