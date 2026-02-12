"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ReactionPicker } from "./reaction-picker";
import type { MessageInfo } from "@/stores/message-store";

interface MessageBubbleProps {
  message: MessageInfo;
  isOwnMessage: boolean;
  currentUserId: string;
  onReaction: (messageId: string, emoji: string) => void;
  onDelete: (messageId: string) => void;
}

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  return words.length >= 2
    ? (words[0][0] + words[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

function formatTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function MessageBubble({
  message,
  isOwnMessage,
  currentUserId,
  onReaction,
  onDelete,
}: MessageBubbleProps) {
  const [showActions, setShowActions] = useState(false);

  const senderName = message.sender?.display_name || message.sender?.username || "Unknown";
  const isDeleted = message.deleted_at !== null;

  const reactionEntries = Object.entries(message.reactions || {});
  const userReactedEmojis = reactionEntries
    .filter(([, userIds]) => userIds.includes(currentUserId))
    .map(([emoji]) => emoji);

  return (
    <div
      className={`group flex gap-2 ${isOwnMessage ? "flex-row-reverse" : "flex-row"}`}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {!isOwnMessage && (
        <Avatar className="size-7 shrink-0 mt-1">
          <AvatarFallback className="text-xs bg-primary/20 text-primary">
            {getInitials(senderName)}
          </AvatarFallback>
        </Avatar>
      )}

      <div className={`max-w-[75%] flex flex-col ${isOwnMessage ? "items-end" : "items-start"}`}>
        <div
          className={`flex items-baseline gap-1.5 mb-0.5 ${isOwnMessage ? "flex-row-reverse" : ""}`}
        >
          {!isOwnMessage && (
            <span className="text-xs font-medium text-foreground">{senderName}</span>
          )}
          <span className="text-[10px] text-muted-foreground">
            {formatTime(message.created_at)}
          </span>
        </div>

        <div className="relative">
          <div
            className={`rounded-xl px-3 py-1.5 text-sm ${
              isDeleted
                ? "bg-muted/50 text-muted-foreground italic"
                : isOwnMessage
                  ? "bg-primary text-primary-foreground rounded-tr-sm"
                  : "bg-muted text-foreground rounded-tl-sm"
            }`}
          >
            {isDeleted ? "Message deleted" : message.content}
          </div>

          {showActions && !isDeleted && (
            <div
              className={`absolute top-0 flex items-center gap-1 ${
                isOwnMessage ? "right-full mr-1" : "left-full ml-1"
              }`}
            >
              <ReactionPicker
                onSelect={(emoji) => onReaction(message.id, emoji)}
                selectedEmojis={userReactedEmojis}
              />
              {isOwnMessage && (
                <button
                  onClick={() => onDelete(message.id)}
                  className="text-muted-foreground hover:text-destructive transition-colors p-0.5"
                  aria-label="Delete message"
                >
                  <Trash2 className="size-3.5" />
                </button>
              )}
            </div>
          )}
        </div>

        {reactionEntries.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {reactionEntries.map(([emoji, userIds]) => {
              const userReacted = userIds.includes(currentUserId);
              return (
                <button
                  key={emoji}
                  onClick={() => onReaction(message.id, emoji)}
                  className={`inline-flex items-center gap-0.5 text-xs rounded-full px-1.5 py-0.5 border transition-colors ${
                    userReacted
                      ? "bg-accent border-primary/30 text-foreground"
                      : "bg-card border-border text-muted-foreground hover:bg-muted"
                  }`}
                >
                  <span>{emoji}</span>
                  <span>{userIds.length}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
