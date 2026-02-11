"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useCreditsStore, useUserStore, useRatingStore, useUIStore } from "@/stores";
import { useSessionStore } from "@/stores/session-store";
import { api, ApiError } from "@/lib/api/client";
import { AppShell } from "@/components/layout";
import { StatCard } from "@/components/ui/stat-card";
import { ReliabilityBadge } from "@/components/ui/reliability-badge";
import { ZeroCreditCard } from "@/components/credits/zero-credit-card";
import { Clock, BookOpen, Flame, Coins, Loader2, Bug, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { VoiceModeModal } from "@/components/session/voice-mode-modal";

// Debug mode: session starts in 1 minute instead of next :00/:30 slot
const DEBUG_WAIT_MINUTES = 1;

export default function DashboardPage() {
  const router = useRouter();
  const t = useTranslations("dashboard");
  const tRating = useTranslations("rating");
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
  const { hasPendingRatings, pendingSessionId, checkPendingRatings } = useRatingStore();
  const openModal = useUIStore((state) => state.openModal);
  const [isMatching, setIsMatching] = useState(false);
  const [debugMode, setDebugMode] = useState(false);
  const [showModeModal, setShowModeModal] = useState(false);

  // Check for pending ratings on mount
  useEffect(() => {
    checkPendingRatings();
  }, [checkPendingRatings]);

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
      toast.success(debugMode ? "Debug Match!" : t("matchFound"), {
        description: debugMode
          ? `Debug mode: Session starts in ${DEBUG_WAIT_MINUTES} minutes`
          : data.is_immediate
            ? t("sessionStartingNow")
            : t("sessionStartsIn", { minutes: data.wait_minutes }),
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
                toast.info(t("rejoiningSession"), {
                  description: t("sessionAlreadyStarted"),
                });
                router.push(`/session/${existingSessionId}`);
              } else {
                // Session hasn't started - go to waiting room
                toast.info(t("alreadyHaveSession"), {
                  description: t("redirectingToWaiting"),
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

      // Handle 402 - insufficient credits (stale frontend state)
      if (error instanceof ApiError && error.status === 402) {
        useCreditsStore.setState({ balance: 0 });
        openModal("upgrade");
        return;
      }

      // Log non-409/non-402 errors
      console.error("Quick match failed:", error);

      const errorMessage =
        error instanceof Error
          ? error.message
          : typeof error === "object" && error !== null && "detail" in error
            ? String((error as { detail: unknown }).detail)
            : t("pleaseTryAgain");
      toast.error(t("failedToJoinTable"), {
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
                {t("welcomeBack", { name: user?.display_name ?? user?.username ?? "Friend" })}
              </h1>
              <p className="mt-1 text-muted-foreground">{t("welcomeSubtitle")}</p>
            </div>
            {user && <ReliabilityBadge score={user.reliability_score} />}
          </div>
        </div>

        {/* Pending ratings alert */}
        {hasPendingRatings && pendingSessionId && (
          <button
            onClick={() => router.push(`/session/${pendingSessionId}/end`)}
            className="w-full rounded-2xl border border-warning/40 bg-warning/5 p-4 text-left transition-colors hover:bg-warning/10"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-warning/20">
                <AlertTriangle className="h-5 w-5 text-warning" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-foreground">{t("pendingRatingsTitle")}</p>
                <p className="text-sm text-muted-foreground">{tRating("pendingDesc")}</p>
              </div>
            </div>
          </button>
        )}

        {/* Zero credits alert */}
        {credits === 0 && <ZeroCreditCard onUpgradeClick={() => openModal("upgrade")} />}

        {/* Stats grid */}
        <div className="grid gap-4 md:grid-cols-3">
          <StatCard
            title={t("sessions")}
            value={user?.session_count ?? 0}
            subtitle={t("completedThisWeek")}
            icon={Clock}
          />
          <StatCard
            title={t("focusTime")}
            value={t("focusMinutes", { minutes: user?.total_focus_minutes ?? 0 })}
            subtitle={t("totalFocusTime")}
            icon={Flame}
          />
          <StatCard
            title={t("credits")}
            value={credits}
            subtitle={t("availableThisWeek")}
            icon={Coins}
          />
        </div>

        {/* Quick actions */}
        <div className="rounded-2xl bg-card p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-foreground">{t("quickActions")}</h2>
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
                  {isMatching ? t("matching") : t("joinTable")}
                </p>
                <p className="text-sm text-muted-foreground">
                  {credits === 0 ? t("noCreditsAvailable") : t("joinStudySession")}
                </p>
              </div>
            </button>
            <button
              onClick={() => router.push("/diary")}
              className="flex items-center gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:bg-muted"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/20 text-success">
                <BookOpen className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-foreground">{t("viewDiary")}</p>
                <p className="text-sm text-muted-foreground">{t("growthJournal")}</p>
              </div>
            </button>
            <button
              onClick={() => openModal("upgrade")}
              className="flex items-center gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:bg-muted"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/20 text-primary">
                <Coins className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-foreground">{t("getMoreCredits")}</p>
                <p className="text-sm text-muted-foreground">{t("upgradePlan")}</p>
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
                Click &quot;Join a Table&quot; to test the flow.
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
