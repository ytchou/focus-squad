"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import type { BoardMessage } from "@/stores/board-store";

interface ChatMessageProps {
  message: BoardMessage;
  isOwnMessage: boolean;
}

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  return words.length >= 2
    ? (words[0][0] + words[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ChatMessage({ message, isOwnMessage }: ChatMessageProps) {
  if (message.type === "system") {
    return (
      <div className="text-center py-1">
        <span className="text-xs text-muted-foreground italic">{message.content}</span>
      </div>
    );
  }

  return (
    <div className={`flex gap-2 ${isOwnMessage ? "flex-row-reverse" : "flex-row"}`}>
      <Avatar className="size-7 shrink-0">
        <AvatarFallback className="text-xs bg-primary/20 text-primary">
          {getInitials(message.displayName)}
        </AvatarFallback>
      </Avatar>

      <div className={`max-w-[75%] ${isOwnMessage ? "items-end" : "items-start"}`}>
        <div className="flex items-baseline gap-1.5 mb-0.5">
          {!isOwnMessage && (
            <span className="text-xs font-medium text-foreground">{message.displayName}</span>
          )}
          <span className="text-[10px] text-muted-foreground">{formatTime(message.timestamp)}</span>
        </div>
        <div
          className={`rounded-xl px-3 py-1.5 text-sm ${
            isOwnMessage
              ? "bg-primary text-primary-foreground rounded-tr-sm"
              : "bg-muted text-foreground rounded-tl-sm"
          }`}
        >
          {message.content}
        </div>
      </div>
    </div>
  );
}
