-- Table invitations for private sessions
CREATE TABLE table_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    inviter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invitee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'accepted', 'declined', 'expired')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ,
    UNIQUE(session_id, invitee_id)
);

CREATE INDEX idx_table_invitations_invitee ON table_invitations(invitee_id);
CREATE INDEX idx_table_invitations_session ON table_invitations(session_id);
CREATE INDEX idx_table_invitations_status ON table_invitations(status);

-- RLS
ALTER TABLE table_invitations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view invitations involving them"
    ON table_invitations FOR SELECT
    USING (
        inviter_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        OR invitee_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "Users can create invitations"
    ON table_invitations FOR INSERT
    WITH CHECK (
        inviter_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "Invitees can update invitation status"
    ON table_invitations FOR UPDATE
    USING (
        invitee_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );
