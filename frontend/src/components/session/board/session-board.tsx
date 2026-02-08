"use client";

import { useEffect, useRef, useCallback } from "react";
import { useBoardStore, type BoardMessage, type ReflectionPhase } from "@/stores/board-store";
import { ChatMessage } from "./chat-message";
import { ReflectionCard } from "./reflection-card";
import { BoardInput } from "./board-input";

interface SessionBoardProps {
  sessionId: string;
  currentUserId: string;
  currentUserDisplayName: string;
  reflectionPhase: ReflectionPhase | null;
  onBroadcastMessage: (message: BoardMessage) => void;
}

export function SessionBoard({
  sessionId,
  currentUserId,
  currentUserDisplayName,
  reflectionPhase,
  onBroadcastMessage,
}: SessionBoardProps) {
  const { messages, isSaving, addMessage, saveReflection, loadSessionReflections } =
    useBoardStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load existing reflections on mount
  useEffect(() => {
    loadSessionReflections(sessionId);
  }, [sessionId, loadSessionReflections]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const handleSendChat = useCallback(
    (content: string) => {
      const message: BoardMessage = {
        id: `chat-${currentUserId}-${Date.now()}`,
        type: "chat",
        userId: currentUserId,
        displayName: currentUserDisplayName,
        content,
        timestamp: Date.now(),
      };
      addMessage(message);
      onBroadcastMessage(message);
    },
    [currentUserId, currentUserDisplayName, addMessage, onBroadcastMessage]
  );

  const handleSendReflection = useCallback(
    (phase: ReflectionPhase, content: string) => {
      const message: BoardMessage = {
        id: `reflection-${currentUserId}-${phase}-${Date.now()}`,
        type: "reflection",
        userId: currentUserId,
        displayName: currentUserDisplayName,
        content,
        timestamp: Date.now(),
        phase,
      };

      // Broadcast to other participants immediately
      onBroadcastMessage(message);

      // Persist to backend (also adds to local store)
      saveReflection(sessionId, phase, content, currentUserId, currentUserDisplayName);
    },
    [sessionId, currentUserId, currentUserDisplayName, onBroadcastMessage, saveReflection]
  );

  return (
    <div className="flex flex-col bg-card rounded-xl border border-border overflow-hidden h-full">
      {/* Message stream */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2 min-h-0">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground py-8">
            {reflectionPhase ? "Share your thoughts with the table!" : "No messages yet"}
          </div>
        )}

        {messages.map((msg) => {
          const isOwn = msg.userId === currentUserId;
          if (msg.type === "reflection") {
            return <ReflectionCard key={msg.id} message={msg} isOwnMessage={isOwn} />;
          }
          return <ChatMessage key={msg.id} message={msg} isOwnMessage={isOwn} />;
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <BoardInput
        currentPhase={reflectionPhase}
        isSaving={isSaving}
        onSendChat={handleSendChat}
        onSendReflection={handleSendReflection}
      />
    </div>
  );
}
