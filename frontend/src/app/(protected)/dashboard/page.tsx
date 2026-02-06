"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useCreditsStore, useUserStore } from "@/stores";
import { useSessionStore } from "@/stores/session-store";
import { api, ApiError } from "@/lib/api/client";
import { AppShell } from "@/components/layout";
import { StatCard } from "@/components/ui/stat-card";
import { ReliabilityBadge } from "@/components/ui/reliability-badge";
import { Clock, Flame, Coins, Loader2, Bug } from "lucide-react";
import { toast } from "sonner";
import { VoiceModeModal } from "@/components/session/voice-mode-modal";

// Debug mode: session starts in 1 minute instead of next :00/:30 slot
const DEBUG_WAIT_MINUTES = 1;

export default function DashboardPage() {
  const router = useRouter();
  const user = useUserStore((state) => state.user);
  const credits = useCreditsStore((state) => state.balance);
  const {
    isWaiting,
    sessionId,
    sessionStartTime,
    setWaitingRoom,
    setLiveKitConnection,
    setQuietMode,
  } = useSessionStore();
  const [isMatching, setIsMatching] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [showModeModal, setShowModeModal] = useState(false);

  // Auto-redirect to waiting room if user has a pending session
  useEffect(() => {
    if (isWaiting && sessionId && sessionStartTime) {
      const now = new Date();
      const startTime = new Date(sessionStartTime);

      if (startTime > now) {
        // Session hasn't started, go to waiting room
        router.push(`/session/${sessionId}/waiting`);
      } else {
        // Session already started, go to active session
        router.push(`/session/${sessionId}`);
      }
    }
  }, [isWaiting, sessionId, sessionStartTime, router]);

  // NOTE: Profile is loaded by AuthProvider on INITIAL_SESSION
  // No need to call refreshProfile here

  const handleQuickMatch = async (mode: "forced_audio" | "quiet") => {
    try {
      setIsMatching(true);

      // Use api client to call FastAPI backend (not Next.js /api route)
      const data = await api.post<{
        session: { id: string; start_time: string; mode: string };
        livekit_token: string;
        wait_minutes: number;
        is_immediate: boolean;
      }>("/sessions/quick-match", {
        filters: { mode },
      });

      // Update session store with waiting room state
      // In debug mode, override start time to 3 minutes from now
      const startTime = debugMode
        ? new Date(Date.now() + DEBUG_WAIT_MINUTES * 60 * 1000)
        : new Date(data.session.start_time);
      const waitMinutes = debugMode ? DEBUG_WAIT_MINUTES : data.wait_minutes;

      setWaitingRoom(startTime, waitMinutes, data.is_immediate);

      // Store quiet mode preference
      setQuietMode(mode === "quiet");

      // Store sessionId for redirect
      useSessionStore.setState({ sessionId: data.session.id });

      // Store LiveKit connection info for session page
      const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;
      if (livekitUrl && data.livekit_token) {
        setLiveKitConnection(data.livekit_token, livekitUrl);
      }

      // Show success toast
      toast.success(debugMode ? "🐛 Debug Match!" : "Match found!", {
        description: debugMode
          ? `Debug mode: Session starts in ${DEBUG_WAIT_MINUTES} minutes`
          : data.is_immediate
            ? "Session starting now!"
            : `Session starts in ${data.wait_minutes} minutes`,
      });

      // Redirect to waiting room
      router.push(`/session/${data.session.id}/waiting`);
    } catch (error: unknown) {
      // Handle 409 Conflict - user already has a session (expected condition)
      if (error instanceof ApiError && error.status === 409) {
        try {
          const detail = JSON.parse(error.message);
          if (detail.detail?.existing_session_id) {
            const existingSessionId = detail.detail.existing_session_id;
            const startTimeStr = detail.detail.start_time;

            if (startTimeStr) {
              const sessionStart = new Date(startTimeStr);
              const now = new Date();

              // Update session store
              setWaitingRoom(sessionStart, 0, false);
              useSessionStore.setState({ sessionId: existingSessionId });

              if (sessionStart <= now) {
                // Session already started - go directly to session
                toast.info("Rejoining your session!", {
                  description: "Your session has already started.",
                });
                router.push(`/session/${existingSessionId}`);
              } else {
                // Session hasn't started - go to waiting room
                toast.info("You already have a session!", {
                  description: "Redirecting to your waiting room...",
                });
                router.push(`/session/${existingSessionId}/waiting`);
              }
              return;
            }
          }
        } catch {
          // JSON parse failed, fall through to generic error
        }
      }

      // Log non-409 errors
      console.error("Quick match failed:", error);

      const errorMessage =
        error instanceof Error
          ? error.message
          : typeof error === "object" && error !== null && "detail" in error
            ? String((error as { detail: unknown }).detail)
            : "Please try again";
      toast.error("Failed to join table", {
        description: errorMessage,
      });
    } finally {
      setIsMatching(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Welcome section */}
        <div className="rounded-2xl bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">
                Welcome back, {user?.display_name ?? user?.username ?? "Friend"}!
              </h1>
              <p className="mt-1 text-muted-foreground">Ready for your next focus session?</p>
            </div>
            {user && <ReliabilityBadge score={user.reliability_score} />}
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid gap-4 md:grid-cols-3">
          <StatCard
            title="Sessions"
            value={user?.session_count ?? 0}
            subtitle="completed this week"
            icon={Clock}
          />
          <StatCard
            title="Focus Time"
            value={`${user?.total_focus_minutes ?? 0} min`}
            subtitle="total focus time"
            icon={Flame}
          />
          <StatCard title="Credits" value={credits} subtitle="available this week" icon={Coins} />
        </div>

        {/* Quick actions */}
        <div className="rounded-2xl bg-card p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-foreground">Quick Actions</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <button
              onClick={() => setShowModeModal(true)}
              disabled={isMatching || credits === 0}
              className="flex items-center gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/20 text-accent">
                {isMatching ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Clock className="h-5 w-5" />
                )}
              </div>
              <div>
                <p className="font-medium text-foreground">
                  {isMatching ? "Matching..." : "Join a Table"}
                </p>
                <p className="text-sm text-muted-foreground">
                  {credits === 0 ? "No credits available" : "Join a study session"}
                </p>
              </div>
            </button>
            <button className="flex items-center gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:bg-muted">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/20 text-success">
                <Flame className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-foreground">View History</p>
                <p className="text-sm text-muted-foreground">Past sessions & stats</p>
              </div>
            </button>
            <button className="flex items-center gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:bg-muted">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/20 text-primary">
                <Coins className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-foreground">Get More Credits</p>
                <p className="text-sm text-muted-foreground">Upgrade your plan</p>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Voice Mode Selection Modal */}
      <VoiceModeModal
        isOpen={showModeModal}
        onClose={() => setShowModeModal(false)}
        onSelect={(mode) => {
          setShowModeModal(false);
          handleQuickMatch(mode);
        }}
        isLoading={isMatching}
      />

      {/* Debug Panel - only in development */}
      {process.env.NODE_ENV === "development" && (
        <div className="fixed bottom-4 right-4 z-50">
          {debugMode ? (
            <div className="bg-card border border-warning rounded-lg shadow-lg p-4 w-64">
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                  <Bug className="h-4 w-4 text-warning" />
                  Debug Mode ON
                </h3>
                <button
                  onClick={() => setDebugMode(false)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  ✕
                </button>
              </div>
              <p className="text-xs text-muted-foreground mb-3">
                Sessions will start in{" "}
                <span className="font-bold text-warning">{DEBUG_WAIT_MINUTES} minute</span> instead
                of the next :00/:30 slot.
              </p>
              <p className="text-xs text-muted-foreground">
                Click "Join a Table" to test the flow.
              </p>
            </div>
          ) : (
            <button
              onClick={() => setDebugMode(true)}
              className="p-2 bg-muted hover:bg-warning text-muted-foreground hover:text-warning-foreground rounded-full shadow-lg transition-colors"
              title="Enable Debug Mode (3-min sessions)"
            >
              <Bug className="h-5 w-5" />
            </button>
          )}
        </div>
      )}
    </AppShell>
  );
}
