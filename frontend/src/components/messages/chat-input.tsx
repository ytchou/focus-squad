"use client";

import { useState, useCallback, type KeyboardEvent } from "react";
import { useTranslations } from "next-intl";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { isBlocked } from "@/lib/moderation/blocklist";
import { useMessageStore } from "@/stores";
import { toast } from "sonner";

const MAX_LENGTH = 1000;

interface ChatInputProps {
  conversationId: string;
  isReadOnly: boolean;
}

export function ChatInput({ conversationId, isReadOnly }: ChatInputProps) {
  const t = useTranslations("messages");
  const [text, setText] = useState("");
  const sendMessage = useMessageStore((s) => s.sendMessage);
  const isSending = useMessageStore((s) => s.isSending);

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed) return;

    if (isBlocked(trimmed)) {
      toast.error(t("messageBlocked"));
      return;
    }

    sendMessage(conversationId, trimmed);
    setText("");
  }, [text, conversationId, sendMessage, t]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isReadOnly) {
    return (
      <div className="flex items-center justify-center p-3 border-t border-border bg-card rounded-b-xl">
        <span className="text-sm text-muted-foreground italic">{t("readOnly")}</span>
      </div>
    );
  }

  const charCount = text.length;
  const showCharCount = charCount > MAX_LENGTH * 0.8;
  const isOverLimit = charCount > MAX_LENGTH;

  return (
    <div className="flex flex-col border-t border-border bg-card rounded-b-xl">
      <div className="flex items-end gap-2 p-3">
        <div className="flex-1 relative">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value.slice(0, MAX_LENGTH))}
            onKeyDown={handleKeyDown}
            placeholder={t("inputPlaceholder")}
            maxLength={MAX_LENGTH}
            rows={1}
            className="w-full resize-none bg-input border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[36px] max-h-[80px]"
            style={{ fieldSizing: "content" } as React.CSSProperties}
          />
        </div>
        <Button
          size="sm"
          onClick={handleSend}
          disabled={!text.trim() || isSending || isOverLimit}
          className="shrink-0 h-9 w-9 p-0"
        >
          <Send className="size-4" />
        </Button>
      </div>

      {showCharCount && (
        <div className="px-4 pb-2 -mt-1">
          <span
            className={`text-[10px] ${isOverLimit ? "text-destructive" : "text-muted-foreground"}`}
          >
            {charCount}/{MAX_LENGTH}
          </span>
        </div>
      )}
    </div>
  );
}
