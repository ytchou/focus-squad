"use client";

import { useState, useCallback, type KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { isBlocked, getMatchedCategory } from "@/lib/moderation/blocklist";
import { api } from "@/lib/api/client";
import { toast } from "sonner";
import type { ReflectionPhase } from "@/stores/board-store";

interface BoardInputProps {
  sessionId: string;
  currentPhase: ReflectionPhase | null;
  isSaving: boolean;
  onSendChat: (content: string) => void;
  onSendReflection: (phase: ReflectionPhase, content: string) => void;
}

const REFLECTION_PROMPTS: Record<ReflectionPhase, string> = {
  setup: "What do you hope to accomplish this session?",
  break: "Quick check-in: how's it going?",
  social: "Any afterthoughts or reflections?",
};

export function BoardInput({
  sessionId,
  currentPhase,
  isSaving,
  onSendChat,
  onSendReflection,
}: BoardInputProps) {
  const [text, setText] = useState("");

  const isReflectionPhase = currentPhase !== null;
  const placeholder = isReflectionPhase ? REFLECTION_PROMPTS[currentPhase] : "Type a message...";

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed) return;

    if (isBlocked(trimmed)) {
      toast.error("Message not sent - please rephrase.");
      if (sessionId) {
        const category = getMatchedCategory(trimmed);
        api
          .post("/moderation/flag", {
            session_id: sessionId,
            content: trimmed,
            matched_pattern: category,
          })
          .catch(() => {});
      }
      return;
    }

    if (isReflectionPhase) {
      onSendReflection(currentPhase, trimmed);
    } else {
      onSendChat(trimmed);
    }
    setText("");
  }, [text, sessionId, isReflectionPhase, currentPhase, onSendChat, onSendReflection]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-end gap-2 p-3 border-t border-border bg-card rounded-b-xl">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        maxLength={500}
        rows={1}
        className="flex-1 resize-none bg-input border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[36px] max-h-[80px]"
        style={{ fieldSizing: "content" } as React.CSSProperties}
      />
      <Button
        size="sm"
        onClick={handleSend}
        disabled={!text.trim() || isSaving}
        className="shrink-0 h-9 w-9 p-0"
      >
        <Send className="size-4" />
      </Button>
    </div>
  );
}
