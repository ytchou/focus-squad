-- Partner Direct Messaging: conversations, members, and messages
-- Supports 1-on-1 (direct) and group chats between accountability partners

-- Conversations (1-on-1 direct or group)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type TEXT NOT NULL CHECK (type IN ('direct', 'group')),
    name TEXT,  -- nullable, only used for group chats
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_type ON conversations(type);
CREATE INDEX idx_conversations_created_by ON conversations(created_by);

-- Conversation membership (who's in each conversation)
CREATE TABLE conversation_members (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    last_read_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (conversation_id, user_id)
);

CREATE INDEX idx_conv_members_user ON conversation_members(user_id);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL CHECK (char_length(content) <= 1000),
    reactions JSONB DEFAULT '{}',
    deleted_at TIMESTAMPTZ,  -- soft delete
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_messages_sender ON messages(sender_id);

-- RLS policies
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Conversations: only members can see
CREATE POLICY "Members can view conversations"
    ON conversations FOR SELECT
    USING (
        id IN (
            SELECT conversation_id FROM conversation_members
            WHERE user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        )
    );

CREATE POLICY "Users can create conversations"
    ON conversations FOR INSERT
    WITH CHECK (
        created_by IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "Creator can update conversations"
    ON conversations FOR UPDATE
    USING (
        created_by IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

-- Conversation members: view co-members, manage own membership
CREATE POLICY "Users can view conversation memberships"
    ON conversation_members FOR SELECT
    USING (
        user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        OR conversation_id IN (
            SELECT conversation_id FROM conversation_members
            WHERE user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        )
    );

CREATE POLICY "Conversation creators can add members"
    ON conversation_members FOR INSERT
    WITH CHECK (
        conversation_id IN (
            SELECT id FROM conversations
            WHERE created_by IN (SELECT id FROM users WHERE auth_id = auth.uid())
        )
        OR user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "Users can update own membership"
    ON conversation_members FOR UPDATE
    USING (
        user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

CREATE POLICY "Users can delete own membership"
    ON conversation_members FOR DELETE
    USING (
        user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

-- Messages: only conversation members can see/send
CREATE POLICY "Members can view messages"
    ON messages FOR SELECT
    USING (
        conversation_id IN (
            SELECT conversation_id FROM conversation_members
            WHERE user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        )
    );

CREATE POLICY "Members can send messages"
    ON messages FOR INSERT
    WITH CHECK (
        sender_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        AND conversation_id IN (
            SELECT conversation_id FROM conversation_members
            WHERE user_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
        )
    );

CREATE POLICY "Sender can update own messages"
    ON messages FOR UPDATE
    USING (
        sender_id IN (SELECT id FROM users WHERE auth_id = auth.uid())
    );

-- Enable Supabase Realtime for live message delivery
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
ALTER PUBLICATION supabase_realtime ADD TABLE conversation_members;
