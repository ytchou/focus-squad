import { useEffect, useRef } from "react";
import { createClient } from "@/lib/supabase/client";
import { useMessageStore, type MessageInfo, type MessageSenderInfo } from "@/stores/message-store";

/**
 * Subscribes to Supabase Realtime for live message delivery and read receipts.
 *
 * - Listens for INSERT events on the `messages` table
 * - Listens for UPDATE events on `conversation_members` (read receipts)
 * - RLS policies ensure users only receive events for their conversations
 *
 * Note: Realtime payloads only contain raw DB columns (no JOINed sender profile).
 * We enrich messages by looking up the sender from the conversation member list.
 */
export function useRealtimeMessages(userId: string | null) {
  const channelRef = useRef<ReturnType<ReturnType<typeof createClient>["channel"]> | null>(null);
  const handleNewMessage = useMessageStore((s) => s.handleNewMessage);
  const handleReadUpdate = useMessageStore((s) => s.handleReadUpdate);

  useEffect(() => {
    if (!userId) return;

    const supabase = createClient();

    const channel = supabase
      .channel(`messages:${userId}`)
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "messages",
        },
        (payload) => {
          const raw = payload.new as MessageInfo;
          // Don't process messages sent by the current user (already in state)
          if (raw.sender_id === userId) return;

          // Realtime payloads lack JOINed sender data. Enrich from conversation members.
          const { conversations } = useMessageStore.getState();
          const conv = conversations.find((c) => c.id === raw.conversation_id);
          const member = conv?.members.find((m) => m.user_id === raw.sender_id);

          const sender: MessageSenderInfo | null = member
            ? {
                user_id: member.user_id,
                username: member.username,
                display_name: member.display_name,
                avatar_config: member.avatar_config,
                pixel_avatar_id: member.pixel_avatar_id,
              }
            : null;

          handleNewMessage({ ...raw, sender, reactions: raw.reactions || {} });
        }
      )
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "conversation_members",
        },
        (payload) => {
          const updated = payload.new as {
            conversation_id: string;
            user_id: string;
            last_read_at: string;
          };
          // Only process other users' read updates
          if (updated.user_id === userId) return;
          handleReadUpdate(updated.conversation_id, updated.user_id, updated.last_read_at);
        }
      )
      .subscribe();

    channelRef.current = channel;

    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId, handleNewMessage, handleReadUpdate]);
}
