"use client";

import type { SessionPhase } from "@/stores/session-store";
import type { BoardMessage, ReflectionPhase } from "@/stores/board-store";
import { PixelRoom } from "./pixel-room";
import { CharacterLayer } from "./character-layer";
import { HudOverlay } from "./hud-overlay";
import { ChatPanel } from "./chat-panel";
import { ControlBar } from "@/components/session/control-bar";
import type { PresenceState } from "@/types/activity";

// Phases where chat panel expands
const BOARD_PHASES: SessionPhase[] = ["setup", "break", "social"];
const REFLECTION_PHASE_MAP: Partial<Record<SessionPhase, ReflectionPhase>> = {
  setup: "setup",
  break: "break",
  social: "social",
};

interface Participant {
  id: string;
  livekitIdentity: string | null;
  seatNumber: number;
  username: string | null;
  displayName: string | null;
  isAI: boolean;
  presenceState: PresenceState;
  isCurrentUser: boolean;
  pixelAvatarId?: string | null;
}

interface PixelSessionLayoutProps {
  sessionId: string;
  roomType: string;
  phase: SessionPhase;
  timeRemaining: number;
  totalTimeRemaining: number;
  participants: Participant[];
  currentUserId: string | null;
  speakingParticipantIds: Set<string>;
  isMuted: boolean;
  isQuietMode: boolean;
  onToggleMute: () => void;
  onLeave: () => Promise<void>;
  onBroadcastMessage?: (message: BoardMessage) => void;
}

export function PixelSessionLayout({
  sessionId,
  roomType,
  phase,
  timeRemaining,
  totalTimeRemaining,
  participants,
  currentUserId,
  speakingParticipantIds,
  isMuted,
  isQuietMode,
  onToggleMute,
  onLeave,
  onBroadcastMessage,
}: PixelSessionLayoutProps) {
  const isBoardPhase = BOARD_PHASES.includes(phase);
  const reflectionPhase = REFLECTION_PHASE_MAP[phase] ?? null;
  const currentUser = participants.find((p) => p.isCurrentUser);
  const currentUserDisplayName = currentUser?.displayName || currentUser?.username || "You";

  return (
    <div className="h-screen w-screen overflow-hidden relative">
      {/* z-0: Room background + z-10: Character sprites */}
      <PixelRoom roomType={roomType}>
        <CharacterLayer
          participants={participants}
          roomType={roomType}
          speakingParticipantIds={speakingParticipantIds}
        />
      </PixelRoom>

      {/* z-20: HUD overlay */}
      <HudOverlay
        sessionId={sessionId}
        phase={phase}
        timeRemaining={timeRemaining}
        totalTimeRemaining={totalTimeRemaining}
        onLeave={onLeave}
      />

      {/* z-20: Chat panel */}
      <ChatPanel
        sessionId={sessionId}
        currentUserId={currentUserId || ""}
        currentUserDisplayName={currentUserDisplayName}
        reflectionPhase={reflectionPhase}
        isExpanded={isBoardPhase}
        onBroadcastMessage={onBroadcastMessage}
      />

      {/* z-20: Control bar */}
      <div className="fixed bottom-0 left-0 right-0 z-20">
        <ControlBar
          isMuted={isMuted}
          isQuietMode={isQuietMode}
          onToggleMute={onToggleMute}
          presenceState={participants.find((p) => p.isCurrentUser)?.presenceState}
        />
      </div>
    </div>
  );
}
