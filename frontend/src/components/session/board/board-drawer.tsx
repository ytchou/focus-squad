"use client";

import { useTranslations } from "next-intl";
import { ChevronUp, ChevronDown, MessageSquare } from "lucide-react";
import { useBoardStore } from "@/stores/board-store";
import type { BoardMessage, ReflectionPhase } from "@/stores/board-store";
import { SessionBoard } from "./session-board";

interface BoardDrawerProps {
  sessionId: string;
  currentUserId: string;
  currentUserDisplayName: string;
  reflectionPhase: ReflectionPhase | null;
  onBroadcastMessage: (message: BoardMessage) => void;
}

export function BoardDrawer({
  sessionId,
  currentUserId,
  currentUserDisplayName,
  reflectionPhase,
  onBroadcastMessage,
}: BoardDrawerProps) {
  const t = useTranslations("session");
  const { isDrawerOpen, unreadCount, setDrawerOpen } = useBoardStore();

  return (
    <div className="fixed bottom-[72px] left-0 right-0 z-20">
      {/* Drawer toggle */}
      <button
        onClick={() => setDrawerOpen(!isDrawerOpen)}
        className="w-full flex items-center justify-center gap-2 py-2 bg-card border-t border-border text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <MessageSquare className="size-4" />
        <span>{isDrawerOpen ? t("hideBoard") : t("sessionBoard")}</span>
        {!isDrawerOpen && unreadCount > 0 && (
          <span className="bg-accent text-accent-foreground text-xs rounded-full px-1.5 py-0.5 min-w-[18px] text-center">
            {unreadCount}
          </span>
        )}
        {isDrawerOpen ? <ChevronDown className="size-4" /> : <ChevronUp className="size-4" />}
      </button>

      {/* Expandable board */}
      {isDrawerOpen && (
        <div className="bg-background border-t border-border h-[300px]">
          <SessionBoard
            sessionId={sessionId}
            currentUserId={currentUserId}
            currentUserDisplayName={currentUserDisplayName}
            reflectionPhase={reflectionPhase}
            onBroadcastMessage={onBroadcastMessage}
          />
        </div>
      )}
    </div>
  );
}
