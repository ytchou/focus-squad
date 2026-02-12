"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { MessageSquare, Users, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useMessageStore } from "@/stores";

interface ConversationListProps {
  currentUserId: string;
  onSelectConversation: (id: string) => void;
  onNewGroup?: () => void;
}

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  return words.length >= 2
    ? (words[0][0] + words[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "now";
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays < 7) return `${diffDays}d`;

  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trimEnd() + "...";
}

export function ConversationList({
  currentUserId,
  onSelectConversation,
  onNewGroup,
}: ConversationListProps) {
  const t = useTranslations("messages");
  const conversations = useMessageStore((s) => s.conversations);
  const activeConversationId = useMessageStore((s) => s.activeConversationId);
  const isLoading = useMessageStore((s) => s.isLoadingConversations);
  const fetchConversations = useMessageStore((s) => s.fetchConversations);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  if (isLoading && conversations.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="size-5 border-2 border-muted-foreground/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
        <MessageSquare className="size-8 text-muted-foreground/50 mb-2" />
        <p className="text-sm text-muted-foreground">{t("noConversations")}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        {conversations.map((conv) => {
          const isActive = conv.id === activeConversationId;
          const isDirect = conv.type === "direct";

          const partner = isDirect ? conv.members.find((m) => m.user_id !== currentUserId) : null;

          const displayName = isDirect
            ? partner?.display_name || partner?.username || t("unknownUser")
            : conv.name || t("groupChat");

          const preview = conv.last_message
            ? conv.last_message.deleted_at
              ? t("messageDeleted")
              : truncate(conv.last_message.content, 60)
            : t("noMessagesYet");

          const timestamp = conv.last_message
            ? formatRelativeTime(conv.last_message.created_at)
            : formatRelativeTime(conv.updated_at);

          return (
            <button
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`w-full flex items-center gap-3 px-3 py-3 text-left transition-colors hover:bg-muted/50 ${
                isActive ? "bg-accent" : ""
              }`}
            >
              {isDirect ? (
                <Avatar className="size-9 shrink-0">
                  <AvatarFallback className="text-xs bg-primary/20 text-primary">
                    {getInitials(displayName)}
                  </AvatarFallback>
                </Avatar>
              ) : (
                <div className="size-9 shrink-0 rounded-full bg-muted flex items-center justify-center">
                  <Users className="size-4 text-muted-foreground" />
                </div>
              )}

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-foreground truncate">
                    {displayName}
                  </span>
                  <span className="text-[10px] text-muted-foreground shrink-0">{timestamp}</span>
                </div>
                <div className="flex items-center justify-between gap-2 mt-0.5">
                  <span className="text-xs text-muted-foreground truncate">{preview}</span>
                  {conv.unread_count > 0 && (
                    <span className="shrink-0 size-5 rounded-full bg-primary text-primary-foreground text-[10px] font-medium flex items-center justify-center">
                      {conv.unread_count > 99 ? "99+" : conv.unread_count}
                    </span>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {onNewGroup && (
        <div className="p-3 border-t border-border">
          <Button variant="outline" size="sm" onClick={onNewGroup} className="w-full text-xs">
            <Plus className="size-3.5 mr-1.5" />
            {t("newGroup")}
          </Button>
        </div>
      )}
    </div>
  );
}
