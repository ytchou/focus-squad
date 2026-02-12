-- Accountability partnerships (bilateral connections with mutual consent)
CREATE TABLE partnerships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    addressee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'declined')),
    last_session_together TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    accepted_at TIMESTAMPTZ,
    CONSTRAINT no_self_partnership CHECK (requester_id != addressee_id),
    UNIQUE(requester_id, addressee_id)
);

CREATE INDEX idx_partnerships_requester ON partnerships(requester_id);
CREATE INDEX idx_partnerships_addressee ON partnerships(addressee_id);
CREATE INDEX idx_partnerships_status ON partnerships(status);

-- RLS
ALTER TABLE partnerships ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own partnerships"
    ON partnerships FOR SELECT
    USING (
        requester_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        OR addressee_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "Users can create partnership requests"
    ON partnerships FOR INSERT
    WITH CHECK (
        requester_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "Users can update partnerships they are part of"
    ON partnerships FOR UPDATE
    USING (
        requester_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        OR addressee_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "Users can delete partnerships they are part of"
    ON partnerships FOR DELETE
    USING (
        requester_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        OR addressee_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );
