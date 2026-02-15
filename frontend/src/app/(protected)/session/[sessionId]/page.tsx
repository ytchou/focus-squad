"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useSessionStore } from "@/stores/session-store";
import { api } from "@/lib/api/client";
import { useSessionTimer } from "@/hooks/use-session-timer";
import { usePresenceDetection } from "@/hooks/use-presence-detection";
import { usePictureInPicture } from "@/hooks/use-picture-in-picture";
import {
  ActivityConsentPrompt,
  getStoredConsent,
} from "@/components/session/activity-consent-prompt";
import type { PresenceState, PresenceMessage } from "@/types/activity";
import {
  SessionLayout,
  SessionHeader,
  TimerDisplay,
  TableView,
  ControlBar,
  CompactTableView,
  SessionBoard,
  BoardDrawer,
} from "@/components/session";
import { PixelSessionLayout } from "@/components/session/pixel";
import {
  LiveKitRoomProvider,
  useActiveSpeakers,
  useLocalMicrophone,
  useDataChannel,
} from "@/components/session/livekit-room-provider";
import { SessionEndModal } from "@/components/session/session-end-modal";
import { useBoardStore, type BoardMessage, type ReflectionPhase } from "@/stores/board-store";
import { toast } from "sonner";
import { Loader2, Bug } from "lucide-react";
import { trackMicToggled } from "@/lib/posthog/events";
import type { SessionPhase } from "@/stores/session-store";

// Debug: Phase minute offsets (how many minutes into session each phase starts)
const DEBUG_PHASE_OFFSETS: Record<SessionPhase, number> = {
  idle: -5, // Before session
  setup: 1, // 1 min into session
  work1: 10, // 10 min into session
  break: 29, // 29 min into session
  work2: 35, // 35 min into session
  social: 51, // 51 min into session
  completed: 56, // After session ends
};

interface SessionApiResponse {
  id: string;
  start_time: string;
  end_time: string;
  mode: "forced_audio" | "quiet";
  topic: string | null;
  language: "en" | "zh-TW";
  current_phase: string;
  phase_started_at: string | null;
  participants: Array<{
    id: string;
    user_id: string | null;
    participant_type: "human" | "ai_companion";
    seat_number: number;
    username: string | null;
    display_name: string | null;
    avatar_config: Record<string, unknown>;
    pixel_avatar_id: string | null;
    joined_at: string;
    is_active: boolean;
    ai_companion_name: string | null;
  }>;
  room_type: string | null;
  available_seats: number;
  livekit_room_name: string;
}

export default function SessionPage() {
  const params = useParams();
  const router = useRouter();
  const t = useTranslations("session");
  const sessionId = params.sessionId as string;

  const {
    sessionStartTime,
    livekitToken,
    livekitServerUrl,
    isQuietMode,
    showEndModal,
    setPhase,
    setQuietMode,
    setShowEndModal,
    leaveSession,
  } = useSessionStore();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<
    Array<{
      id: string;
      userId: string | null;
      livekitIdentity: string | null; // LiveKit identity (user_id for humans, null for AI)
      seatNumber: number;
      username: string | null;
      displayName: string | null;
      isAI: boolean;
      isMuted: boolean;
      presenceState: PresenceState;
      isCurrentUser: boolean;
      pixelAvatarId?: string | null;
      isTyping?: boolean;
    }>
  >([]);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [roomType, setRoomType] = useState<string>("cozy-study");
  const [viewMode, setViewMode] = useState<"pixel" | "classic">(() => {
    if (typeof window !== "undefined") {
      return (localStorage.getItem("sessionViewMode") as "pixel" | "classic") || "pixel";
    }
    return "pixel";
  });

  // Fetch session data on mount
  useEffect(() => {
    async function fetchSession() {
      try {
        const session = await api.get<SessionApiResponse>(`/sessions/${sessionId}`);

        // Set quiet mode based on session mode
        setQuietMode(session.mode === "quiet");

        // Get current user ID and tier from the API
        const userProfile = await api.get<{ id: string; credit_tier: string }>("/users/me");
        const userId = userProfile.id;
        setCurrentUserId(userId);
        setIsAdmin(userProfile.credit_tier === "admin");

        // Set room type from session data
        setRoomType(session.room_type || "cozy-study");

        // Map participants to our format
        // Note: LiveKit identity is the user_id, used for speaking detection
        const mappedParticipants = session.participants.map((p) => ({
          id: p.id,
          userId: p.user_id,
          livekitIdentity: p.user_id, // LiveKit uses user_id as participant identity
          seatNumber: p.seat_number,
          username: p.username,
          displayName: p.display_name || p.ai_companion_name,
          isAI: p.participant_type === "ai_companion",
          isMuted: false, // Will be updated by LiveKit
          presenceState: "active" as PresenceState, // Default; overridden by presence detection
          isCurrentUser: p.user_id === userId,
          pixelAvatarId: p.pixel_avatar_id,
        }));

        setParticipants(mappedParticipants);
        setIsLoading(false);
      } catch (err) {
        console.error("Failed to fetch session:", err);
        setError(t("failedToLoad"));
        setIsLoading(false);
      }
    }

    fetchSession();
  }, [sessionId, setQuietMode, t]);

  // Poll for participant updates (AI companions are added at T+5s after session start)
  // Stop polling once we have 4 participants or after 30 seconds
  useEffect(() => {
    if (isLoading || participants.length >= 4) return;

    const pollInterval = setInterval(async () => {
      try {
        const session = await api.get<SessionApiResponse>(`/sessions/${sessionId}`);
        const mappedParticipants = session.participants.map((p) => ({
          id: p.id,
          userId: p.user_id,
          livekitIdentity: p.user_id,
          seatNumber: p.seat_number,
          username: p.username,
          displayName: p.display_name || p.ai_companion_name,
          isAI: p.participant_type === "ai_companion",
          isMuted: false,
          presenceState: "active" as PresenceState,
          isCurrentUser: p.user_id === currentUserId,
          pixelAvatarId: p.pixel_avatar_id,
        }));

        // Only update if participant count changed
        if (mappedParticipants.length !== participants.length) {
          setParticipants(mappedParticipants);
        }

        // Stop polling when table is full
        if (mappedParticipants.length >= 4) {
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error("Failed to poll participants:", err);
      }
    }, 5000); // Poll every 5 seconds

    // Stop polling after 30 seconds regardless
    const timeout = setTimeout(() => {
      clearInterval(pollInterval);
    }, 30000);

    return () => {
      clearInterval(pollInterval);
      clearTimeout(timeout);
    };
  }, [sessionId, isLoading, participants.length, currentUserId]);

  // Phase change handler
  const handlePhaseChange = useCallback(
    (newPhase: SessionPhase, _previousPhase: SessionPhase) => {
      setPhase(newPhase);

      // Show end modal when entering social or completed phase
      if (newPhase === "social" || newPhase === "completed") {
        setShowEndModal(true);
      }

    },
    [setPhase, setShowEndModal]
  );

  // Session timer
  const { phase, timeRemaining, totalTimeRemaining, progress } = useSessionTimer({
    sessionStartTime,
    onPhaseChange: handlePhaseChange,
  });

  // Consent for input tracking (keyboard/mouse)
  const [inputTrackingConsent, setInputTrackingConsent] = useState<boolean>(
    () => getStoredConsent() === "granted"
  );
  const [showConsentPrompt, setShowConsentPrompt] = useState(() => getStoredConsent() === null);

  // PiP state (set by SessionPageContent, consumed by presence detection)
  const [isPiPActive, setIsPiPActive] = useState(false);

  // Presence detection (replaces useActivityTracking)
  const { presenceState: myPresenceState, isTyping: myIsTyping } = usePresenceDetection({
    enabled: true,
    inputTrackingConsent,
    isPiPActive,
  });

  // Leave session handler
  const handleLeave = async () => {
    try {
      await api.post(`/sessions/${sessionId}/leave`);
      leaveSession();
    } catch (err) {
      console.error("Failed to leave session:", err);
    }
  };

  // Handle end modal close
  const handleEndModalClose = () => {
    setShowEndModal(false);
    if (phase === "completed") {
      router.push(`/session/${sessionId}/end`);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">{t("loadingSession")}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="text-center">
          <p className="text-destructive mb-4">{error}</p>
          <button onClick={() => router.push("/dashboard")} className="text-primary underline">
            {t("returnToDashboard")}
          </button>
        </div>
      </div>
    );
  }

  // Consent prompt (rendered in both LiveKit and non-LiveKit paths)
  const consentPrompt = showConsentPrompt ? (
    <ActivityConsentPrompt
      onConsent={(granted) => {
        setInputTrackingConsent(granted);
        setShowConsentPrompt(false);
      }}
    />
  ) : null;

  // Enhance participants with current user's local presence (non-LiveKit path)
  const enhancedParticipants = participants.map((p) =>
    p.isCurrentUser ? { ...p, presenceState: myPresenceState, isTyping: myIsTyping } : p
  );

  // If we have a LiveKit token, wrap in LiveKit provider
  if (livekitToken && livekitServerUrl) {
    return (
      <>
        <LiveKitRoomProvider
          token={livekitToken}
          serverUrl={livekitServerUrl}
          isQuietMode={isQuietMode}
        >
          <LiveKitSessionContent
            sessionId={sessionId}
            phase={phase}
            timeRemaining={timeRemaining}
            totalTimeRemaining={totalTimeRemaining}
            progress={progress}
            participants={participants}
            currentUserId={currentUserId}
            isQuietMode={isQuietMode}
            showEndModal={showEndModal}
            onLeave={handleLeave}
            onEndModalClose={handleEndModalClose}
            isAdmin={isAdmin}
            roomType={roomType}
            viewMode={viewMode}
            setViewMode={setViewMode}
            myPresenceState={myPresenceState}
            myIsTyping={myIsTyping}
            onPiPActiveChange={setIsPiPActive}
          />
        </LiveKitRoomProvider>
        {consentPrompt}
      </>
    );
  }

  // Fallback without LiveKit (for testing or when token not available)
  return (
    <>
      <SessionPageContent
        sessionId={sessionId}
        phase={phase}
        timeRemaining={timeRemaining}
        totalTimeRemaining={totalTimeRemaining}
        progress={progress}
        participants={enhancedParticipants}
        currentUserId={currentUserId}
        isQuietMode={isQuietMode}
        showEndModal={showEndModal}
        onLeave={handleLeave}
        onEndModalClose={handleEndModalClose}
        disableAudio={true}
        isAdmin={isAdmin}
        roomType={roomType}
        viewMode={viewMode}
        setViewMode={setViewMode}
        onPiPActiveChange={setIsPiPActive}
      />
      {consentPrompt}
    </>
  );
}

// Wrapper component that uses LiveKit hooks (must be inside LiveKitRoomProvider)
function LiveKitSessionContent(
  props: Omit<SessionPageContentProps, "disableAudio"> & {
    myPresenceState: PresenceState;
    myIsTyping: boolean;
  }
) {
  const { isMuted, toggleMute } = useLocalMicrophone();
  const speakingParticipantIds = useActiveSpeakers();
  const { addMessage, incrementUnread, isDrawerOpen } = useBoardStore();

  // Remote participants' presence states and typing status
  const [presenceMap, setPresenceMap] = useState<Map<string, PresenceState>>(new Map());
  const [typingMap, setTypingMap] = useState<Map<string, boolean>>(new Map());

  // Receive data channel messages from other participants
  const handleDataMessage = useCallback(
    (data: unknown) => {
      const msg = data as Record<string, unknown>;
      if (!msg?.type || !msg?.userId || msg.userId === props.currentUserId) return;

      // Handle presence messages
      if (msg.type === "presence") {
        const presenceMsg = msg as unknown as PresenceMessage;
        setPresenceMap((prev) => {
          const next = new Map(prev);
          next.set(presenceMsg.userId, presenceMsg.presenceState);
          return next;
        });
        setTypingMap((prev) => {
          const next = new Map(prev);
          next.set(presenceMsg.userId, presenceMsg.isTyping);
          return next;
        });
        return;
      }

      // Handle board messages (reflections, chat, etc.)
      const boardMsg = data as BoardMessage;
      addMessage(boardMsg);
      if (!isDrawerOpen) {
        incrementUnread();
      }
    },
    [props.currentUserId, addMessage, incrementUnread, isDrawerOpen]
  );

  const { sendMessage } = useDataChannel(handleDataMessage);

  // Broadcast presence on state changes
  const myPresenceRef = useRef(props.myPresenceState);
  const myTypingRef = useRef(props.myIsTyping);
  useEffect(() => {
    myPresenceRef.current = props.myPresenceState;
  }, [props.myPresenceState]);
  useEffect(() => {
    myTypingRef.current = props.myIsTyping;
  }, [props.myIsTyping]);

  useEffect(() => {
    if (!props.currentUserId) return;
    sendMessage({
      type: "presence",
      userId: props.currentUserId,
      presenceState: props.myPresenceState,
      isTyping: props.myIsTyping,
      timestamp: Date.now(),
    } satisfies PresenceMessage);
  }, [props.myPresenceState, props.myIsTyping, props.currentUserId, sendMessage]);

  // Periodic keepalive broadcast every 30s (for late joiners)
  useEffect(() => {
    const userId = props.currentUserId;
    if (!userId) return;
    const interval = setInterval(() => {
      sendMessage({
        type: "presence",
        userId,
        presenceState: myPresenceRef.current,
        isTyping: myTypingRef.current,
        timestamp: Date.now(),
      } satisfies PresenceMessage);
    }, 30_000);
    return () => clearInterval(interval);
  }, [props.currentUserId, sendMessage]);

  // Merge presence and typing into participants
  const enhancedParticipants = props.participants.map((p) => {
    if (p.isCurrentUser) {
      return { ...p, presenceState: props.myPresenceState, isTyping: props.myIsTyping };
    }
    if (p.isAI) return p; // AI companions stay "active"
    const remoteState = p.livekitIdentity ? presenceMap.get(p.livekitIdentity) : undefined;
    const remoteTyping = p.livekitIdentity ? typingMap.get(p.livekitIdentity) : undefined;
    return {
      ...p,
      ...(remoteState !== undefined && { presenceState: remoteState }),
      ...(remoteTyping !== undefined && { isTyping: remoteTyping }),
    };
  });

  // Broadcast board messages to other participants
  const handleBroadcastMessage = useCallback(
    (message: BoardMessage) => {
      sendMessage(message);
    },
    [sendMessage]
  );

  return (
    <SessionPageContent
      {...props}
      participants={enhancedParticipants}
      isMuted={isMuted}
      toggleMute={toggleMute}
      speakingParticipantIds={speakingParticipantIds}
      onBroadcastMessage={handleBroadcastMessage}
    />
  );
}

interface SessionPageContentProps {
  sessionId: string;
  phase: SessionPhase;
  timeRemaining: number;
  totalTimeRemaining: number;
  progress: number;
  participants: Array<{
    id: string;
    userId: string | null;
    livekitIdentity: string | null;
    seatNumber: number;
    username: string | null;
    displayName: string | null;
    isAI: boolean;
    isMuted: boolean;
    presenceState: PresenceState;
    isCurrentUser: boolean;
    pixelAvatarId?: string | null;
    isTyping?: boolean;
  }>;
  currentUserId: string | null;
  isQuietMode: boolean;
  showEndModal: boolean;
  onLeave: () => Promise<void>;
  onEndModalClose: () => void;
  disableAudio?: boolean;
  isAdmin?: boolean;
  // LiveKit state (optional - defaults used when outside LiveKit context)
  isMuted?: boolean;
  toggleMute?: () => void;
  speakingParticipantIds?: Set<string>;
  // Board data channel (only available inside LiveKit context)
  onBroadcastMessage?: (message: BoardMessage) => void;
  // Pixel art view mode
  roomType: string;
  viewMode: "pixel" | "classic";
  setViewMode: (mode: "pixel" | "classic") => void;
  // PiP state callback
  onPiPActiveChange?: (active: boolean) => void;
}

// Phases where the board takes over the main content area
const BOARD_PHASES: SessionPhase[] = ["setup", "break", "social"];
// Phases that correspond to reflection prompts
const REFLECTION_PHASE_MAP: Partial<Record<SessionPhase, ReflectionPhase>> = {
  setup: "setup",
  break: "break",
  social: "social",
};

function SessionPageContent({
  sessionId,
  phase,
  timeRemaining,
  totalTimeRemaining,
  progress,
  participants,
  currentUserId,
  isQuietMode,
  showEndModal,
  onLeave,
  onEndModalClose,
  disableAudio = false,
  isAdmin = false,
  isMuted = true,
  toggleMute = () => {},
  speakingParticipantIds = new Set<string>(),
  onBroadcastMessage,
  roomType,
  viewMode,
  setViewMode,
  onPiPActiveChange,
}: SessionPageContentProps) {
  const t = useTranslations("session");
  const isBoardPhase = BOARD_PHASES.includes(phase);
  const reflectionPhase = REFLECTION_PHASE_MAP[phase] ?? null;
  const currentUser = participants.find((p) => p.isCurrentUser);
  const currentUserDisplayName = currentUser?.displayName || currentUser?.username || t("you");

  // Wrap mic toggle with PostHog tracking
  const handleToggleMute = useCallback(() => {
    trackMicToggled(sessionId, phase, isMuted); // isMuted is current state; after toggle it will be !isMuted
    toggleMute();
  }, [sessionId, phase, isMuted, toggleMute]);

  // Picture-in-Picture mini view
  const { isPiPActive, isPiPSupported, togglePiP } = usePictureInPicture({
    phase,
    timeRemaining,
    participants: participants.map((p) => ({
      displayName: p.displayName,
      presenceState: p.presenceState,
    })),
  });

  // Sync PiP active state back to parent for presence detection
  useEffect(() => {
    onPiPActiveChange?.(isPiPActive);
  }, [isPiPActive, onPiPActiveChange]);

  // Persist view mode to localStorage
  useEffect(() => {
    localStorage.setItem("sessionViewMode", viewMode);
  }, [viewMode]);

  // Phase nudge: show toast when entering a reflection phase
  const prevPhaseRef = useRef<SessionPhase>(phase);
  useEffect(() => {
    if (phase !== prevPhaseRef.current && reflectionPhase) {
      const prompts: Record<ReflectionPhase, string> = {
        setup: t("phaseNudgeSetup"),
        break: t("phaseNudgeBreak"),
        social: t("phaseNudgeSocial"),
      };
      toast.info(prompts[reflectionPhase]);
    }
    prevPhaseRef.current = phase;
  }, [phase, reflectionPhase, t]);

  // Reset board store when session ends or user navigates away
  useEffect(() => {
    if (phase === "completed") {
      useBoardStore.getState().reset();
    }
  }, [phase]);

  const handleBroadcast = useCallback(
    (message: BoardMessage) => {
      onBroadcastMessage?.(message);
    },
    [onBroadcastMessage]
  );

  // Pixel art view mode
  if (viewMode === "pixel") {
    return (
      <>
        <PixelSessionLayout
          sessionId={sessionId}
          roomType={roomType}
          phase={phase}
          timeRemaining={timeRemaining}
          totalTimeRemaining={totalTimeRemaining}
          participants={participants}
          currentUserId={currentUserId}
          speakingParticipantIds={speakingParticipantIds}
          isMuted={isMuted}
          isQuietMode={isQuietMode || disableAudio}
          onToggleMute={handleToggleMute}
          onLeave={onLeave}
          onBroadcastMessage={handleBroadcast}
          isPiPActive={isPiPActive}
          isPiPSupported={isPiPSupported}
          onTogglePiP={togglePiP}
        />

        {/* Session End Modal */}
        <SessionEndModal
          open={showEndModal}
          onClose={onEndModalClose}
          sessionId={sessionId}
          phase={phase}
        />

        {/* View mode toggle */}
        <button
          onClick={() => setViewMode("classic")}
          className="fixed bottom-4 left-4 z-30 px-3 py-1.5 text-xs bg-foreground/60 backdrop-blur-sm text-primary-foreground rounded-lg hover:bg-foreground/70 transition-colors"
          title={t("switchToClassic")}
        >
          {t("classicView")}
        </button>

        {/* Debug Panel - only for admin users */}
        {isAdmin && <DebugPanel currentPhase={phase} sessionId={sessionId} />}
      </>
    );
  }

  // Classic view mode
  return (
    <>
      <SessionLayout
        header={<SessionHeader sessionId={sessionId} phase={phase} onLeave={onLeave} />}
        controls={
          <ControlBar
            isMuted={isMuted}
            isQuietMode={isQuietMode || disableAudio}
            onToggleMute={handleToggleMute}
            presenceState={currentUser?.presenceState}
            isPiPActive={isPiPActive}
            isPiPSupported={isPiPSupported}
            onTogglePiP={togglePiP}
          />
        }
      >
        {isBoardPhase ? (
          <>
            {/* Board phase: compact table + timer badge + board as main content */}
            <CompactTableView
              participants={participants}
              speakingParticipantIds={speakingParticipantIds}
            />
            <div className="text-center mb-3">
              <TimerDisplay
                phase={phase}
                timeRemaining={timeRemaining}
                totalTimeRemaining={totalTimeRemaining}
                progress={progress}
                compact
              />
            </div>
            <div className="w-full max-w-lg flex-1 min-h-0">
              <SessionBoard
                sessionId={sessionId}
                currentUserId={currentUserId || ""}
                currentUserDisplayName={currentUserDisplayName}
                reflectionPhase={reflectionPhase}
                onBroadcastMessage={handleBroadcast}
              />
            </div>
          </>
        ) : (
          <>
            {/* Work phase: timer + full table (board in drawer) */}
            <div className="mb-8">
              <TimerDisplay
                phase={phase}
                timeRemaining={timeRemaining}
                totalTimeRemaining={totalTimeRemaining}
                progress={progress}
              />
            </div>
            <TableView
              participants={participants}
              speakingParticipantIds={speakingParticipantIds}
              currentUserId={currentUserId}
              sessionId={sessionId}
            />
          </>
        )}
      </SessionLayout>

      {/* Board drawer during work phases */}
      {!isBoardPhase && phase !== "idle" && phase !== "completed" && (
        <BoardDrawer
          sessionId={sessionId}
          currentUserId={currentUserId || ""}
          currentUserDisplayName={currentUserDisplayName}
          reflectionPhase={null}
          onBroadcastMessage={handleBroadcast}
        />
      )}

      {/* View mode toggle */}
      <button
        onClick={() => setViewMode("pixel")}
        className="fixed bottom-20 left-4 z-30 px-3 py-1.5 text-xs bg-primary/80 text-primary-foreground rounded-lg hover:bg-primary transition-colors"
        title={t("switchToPixel")}
      >
        {t("pixelView")}
      </button>

      {/* Session End Modal */}
      <SessionEndModal
        open={showEndModal}
        onClose={onEndModalClose}
        sessionId={sessionId}
        phase={phase}
      />

      {/* Debug Panel - only for admin users */}
      {isAdmin && <DebugPanel currentPhase={phase} sessionId={sessionId} />}
    </>
  );
}

// =============================================================================
// Debug Panel (Development Only)
// =============================================================================

function DebugPanel({
  currentPhase,
  sessionId,
}: {
  currentPhase: SessionPhase;
  sessionId: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  const jumpToPhase = async (targetPhase: SessionPhase) => {
    const offsetMinutes = DEBUG_PHASE_OFFSETS[targetPhase];
    const fakeStartTime = new Date(Date.now() - offsetMinutes * 60 * 1000);
    useSessionStore.setState({ sessionStartTime: fakeStartTime });

    // When jumping to "completed", trigger stats update via debug endpoint
    if (targetPhase === "completed") {
      setIsUpdating(true);
      try {
        await api.post(`/sessions/${sessionId}/debug/complete`);
        console.log("[DEBUG] Session stats updated");
      } catch (err) {
        console.error("[DEBUG] Failed to update session stats:", err);
      } finally {
        setIsUpdating(false);
      }
    }
  };

  const phases: SessionPhase[] = ["setup", "work1", "break", "work2", "social", "completed"];

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 p-2 bg-warning text-warning-foreground rounded-full shadow-lg hover:bg-warning/90 z-50"
        title="Open Debug Panel"
      >
        <Bug className="h-5 w-5" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 p-4 bg-card border border-border rounded-lg shadow-lg z-50 w-64">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold text-sm">🐛 Debug Panel</h3>
        <button
          onClick={() => setIsOpen(false)}
          className="text-muted-foreground hover:text-foreground"
        >
          ✕
        </button>
      </div>

      <div className="space-y-2">
        <p className="text-xs text-muted-foreground">
          Current: <span className="font-mono text-primary">{currentPhase}</span>
        </p>

        <div className="text-xs font-medium text-muted-foreground mb-1">Jump to phase:</div>
        <div className="grid grid-cols-2 gap-1">
          {phases.map((phase) => (
            <button
              key={phase}
              onClick={() => jumpToPhase(phase)}
              disabled={phase === currentPhase || isUpdating}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                phase === currentPhase
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted hover:bg-muted/80 text-foreground"
              }`}
            >
              {phase}
            </button>
          ))}
        </div>

        <div className="pt-2 border-t border-border mt-2">
          <button
            onClick={() => useSessionStore.setState({ showEndModal: true })}
            className="w-full px-2 py-1 text-xs bg-accent text-accent-foreground rounded hover:bg-accent/90"
          >
            Show End Modal
          </button>
        </div>

        {isUpdating && (
          <p className="text-xs text-muted-foreground animate-pulse">Updating stats...</p>
        )}
      </div>
    </div>
  );
}
