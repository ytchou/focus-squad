import { useEffect, useRef } from "react";
import { createClient } from "@/lib/supabase/client";
import { useMessageStore, type MessageInfo } from "@/stores/message-store";

/**
 * Subscribes to Supabase Realtime for live message delivery and read receipts.
 *
 * - Listens for INSERT events on the `messages` table
 * - Listens for UPDATE events on `conversation_members` (read receipts)
 * - RLS policies ensure users only receive events for their conversations
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
          const newMessage = payload.new as MessageInfo;
          // Don't process messages sent by the current user (already in state)
          if (newMessage.sender_id === userId) return;
          handleNewMessage(newMessage);
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
