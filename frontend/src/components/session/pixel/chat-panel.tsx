"use client";

import { useState } from "react";
import { MessageSquare, ChevronRight, ChevronLeft } from "lucide-react";
import { SessionBoard } from "@/components/session/board/session-board";
import { useBoardStore, type BoardMessage, type ReflectionPhase } from "@/stores/board-store";
import { cn } from "@/lib/utils";

const noop = () => {};

interface ChatPanelProps {
  sessionId: string;
  currentUserId: string;
  currentUserDisplayName: string;
  reflectionPhase: ReflectionPhase | null;
  isExpanded: boolean; // true during board/reflection phases
  onBroadcastMessage?: (message: BoardMessage) => void;
}

export function ChatPanel({
  sessionId,
  currentUserId,
  currentUserDisplayName,
  reflectionPhase,
  isExpanded,
  onBroadcastMessage,
}: ChatPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { unreadCount } = useBoardStore();

  const panelWidth = isExpanded ? "w-96" : "w-72";

  if (isCollapsed) {
    return (
      <button
        onClick={() => setIsCollapsed(false)}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-20 bg-foreground/60 backdrop-blur-sm text-white p-3 rounded-l-xl hover:bg-foreground/70 transition-colors"
      >
        <div className="flex flex-col items-center gap-1">
          <ChevronLeft className="h-5 w-5" />
          <MessageSquare className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="bg-accent text-accent-foreground text-xs rounded-full px-1.5 py-0.5 min-w-[1.25rem] text-center">
              {unreadCount}
            </span>
          )}
        </div>
      </button>
    );
  }

  return (
    <div
      className={cn(
        "fixed right-0 top-12 bottom-16 z-20 bg-surface/90 backdrop-blur-sm border-l border-border/50 flex flex-col transition-all duration-300",
        panelWidth
      )}
    >
      {/* Header with collapse button */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border/50">
        <span className="text-sm font-medium text-foreground">
          {reflectionPhase ? "Reflections" : "Chat"}
        </span>
        <button
          onClick={() => setIsCollapsed(true)}
          className="text-muted-foreground hover:text-foreground p-1"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Session Board (reused as-is) */}
      <div className="flex-1 min-h-0">
        <SessionBoard
          sessionId={sessionId}
          currentUserId={currentUserId}
          currentUserDisplayName={currentUserDisplayName}
          reflectionPhase={reflectionPhase}
          onBroadcastMessage={onBroadcastMessage || noop}
        />
      </div>
    </div>
  );
}
