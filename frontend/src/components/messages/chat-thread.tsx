"use client";

import { useRef, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useMessageStore } from "@/stores";
import { MessageBubble } from "./message-bubble";

interface ChatThreadProps {
  conversationId: string;
  currentUserId: string;
}

function formatDateSeparator(dateStr: string): string {
  const date = new Date(dateStr);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";

  return date.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function getDateKey(dateStr: string): string {
  return new Date(dateStr).toDateString();
}

export function ChatThread({ conversationId, currentUserId }: ChatThreadProps) {
  const t = useTranslations("messages");
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevMessageCountRef = useRef(0);

  const messages = useMessageStore((s) => s.messages[conversationId] || []);
  const isLoadingMessages = useMessageStore((s) => s.isLoadingMessages);
  const hasMore = useMessageStore((s) => s.hasMore[conversationId] ?? false);
  const loadMoreMessages = useMessageStore((s) => s.loadMoreMessages);
  const toggleReaction = useMessageStore((s) => s.toggleReaction);
  const deleteMessage = useMessageStore((s) => s.deleteMessage);

  const handleReaction = useCallback(
    (messageId: string, emoji: string) => {
      toggleReaction(messageId, emoji);
    },
    [toggleReaction]
  );

  const handleDelete = useCallback(
    (messageId: string) => {
      deleteMessage(messageId);
    },
    [deleteMessage]
  );

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messages.length > prevMessageCountRef.current) {
      const el = scrollRef.current;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    }
    prevMessageCountRef.current = messages.length;
  }, [messages.length]);

  // Messages are stored newest-first in the store, reverse for display
  const displayMessages = [...messages].reverse();

  // Group messages by date for date separators
  const groupedMessages: { date: string; messages: typeof displayMessages }[] = [];
  let currentDateKey = "";
  for (const msg of displayMessages) {
    const dateKey = getDateKey(msg.created_at);
    if (dateKey !== currentDateKey) {
      currentDateKey = dateKey;
      groupedMessages.push({ date: msg.created_at, messages: [msg] });
    } else {
      groupedMessages[groupedMessages.length - 1].messages.push(msg);
    }
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-3">
      {/* Load more button */}
      {hasMore && (
        <div className="flex justify-center py-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => loadMoreMessages(conversationId)}
            disabled={isLoadingMessages}
            className="text-xs text-muted-foreground"
          >
            {isLoadingMessages ? (
              <>
                <Loader2 className="size-3 mr-1 animate-spin" />
                {t("loading")}
              </>
            ) : (
              t("loadMore")
            )}
          </Button>
        </div>
      )}

      {/* Loading state for initial load */}
      {isLoadingMessages && messages.length === 0 && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="size-5 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Empty state */}
      {!isLoadingMessages && messages.length === 0 && (
        <div className="flex items-center justify-center py-8">
          <p className="text-sm text-muted-foreground">{t("noMessages")}</p>
        </div>
      )}

      {/* Messages grouped by date */}
      {groupedMessages.map((group) => (
        <div key={group.date}>
          <div className="flex items-center gap-2 py-2">
            <div className="flex-1 h-px bg-border" />
            <span className="text-[10px] text-muted-foreground font-medium px-2">
              {formatDateSeparator(group.date)}
            </span>
            <div className="flex-1 h-px bg-border" />
          </div>

          <div className="space-y-2">
            {group.messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isOwnMessage={msg.sender_id === currentUserId}
                currentUserId={currentUserId}
                onReaction={handleReaction}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
