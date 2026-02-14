"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  useCreditsStore,
  useUserStore,
  useRatingStore,
  useUIStore,
  usePartnerStore,
  useGamificationStore,
  type WeeklyStreakResponse,
  type RateableUser,
  type InvitationInfo,
} from "@/stores";
import { useSessionStore } from "@/stores/session-store";
import { api, ApiError } from "@/lib/api/client";
import { AppShell } from "@/components/layout";
import { StatCard } from "@/components/ui/stat-card";
import { ReliabilityBadge } from "@/components/ui/reliability-badge";
import { ZeroCreditCard } from "@/components/credits/zero-credit-card";
import { FindTableHero } from "@/components/session/find-table-hero";
import { StreakProgressBar } from "@/components/room/streak-progress-bar";
import { Clock, BookOpen, Flame, Coins, Bug, AlertTriangle, Users2 } from "lucide-react";
import { toast } from "sonner";
import { InvitationAlert } from "@/components/partners";

// Debug mode: session starts in 1 minute instead of next :00/:30 slot
const DEBUG_WAIT_MINUTES = 1;

interface DashboardInitResponse {
  pending_ratings: {
    has_pending: boolean;
    pending: {
      session_id: string;
      rateable_users: RateableUser[];
      expires_at: string;
    } | null;
  };
  invitations: InvitationInfo[];
  streak: WeeklyStreakResponse;
  upcoming_slots: {
    slots: Array<{
      start_time: string;
      queue_count: number;
      estimated_count: number;
      has_user_session: boolean;
    }>;
  };
}

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
  const { hasPendingRatings, pendingSessionId, setPendingRatings } = useRatingStore();
  const { pendingInvitations, respondToInvitation } = usePartnerStore();
  const { weeklyStreak } = useGamificationStore();
  const openModal = useUIStore((state) => state.openModal);
  const tPartners = useTranslations("partners");
  const [isMatching, setIsMatching] = useState(false);
  const [matchingSlot, setMatchingSlot] = useState<string | null>(null);
  const [debugMode, setDebugMode] = useState(false);
  const [initialSlots, setInitialSlots] = useState<
    DashboardInitResponse["upcoming_slots"]["slots"] | undefined
  >(undefined);

  // Batch fetch all dashboard data in a single API call
  const fetchDashboardInit = useCallback(async () => {
    try {
      const data = await api.get<DashboardInitResponse>("/api/v1/dashboard/init?mode=forced_audio");

      // Hydrate rating store
      if (
        data.pending_ratings.has_pending &&
        data.pending_ratings.pending &&
        data.pending_ratings.pending.rateable_users.length > 0
      ) {
        setPendingRatings(
          data.pending_ratings.pending.session_id,
          data.pending_ratings.pending.rateable_users
        );
      } else {
        useRatingStore.setState({ hasPendingRatings: false, pendingSessionId: null });
      }

      // Hydrate partner store (invitations)
      usePartnerStore.setState({ pendingInvitations: data.invitations });

      // Hydrate gamification store (streak)
      useGamificationStore.setState({ weeklyStreak: data.streak });

      // Set initial slots for FindTableHero
      setInitialSlots(data.upcoming_slots.slots);
    } catch (err) {
      console.warn("Dashboard init fetch failed:", err);
    }
  }, [setPendingRatings]);

  useEffect(() => {
    fetchDashboardInit();
  }, [fetchDashboardInit]);

  const handleInvitationRespond = async (
    sessionId: string,
    invitationId: string,
    accept: boolean
  ) => {
    try {
      await respondToInvitation(sessionId, invitationId, accept);
      toast.success(accept ? tPartners("invitationAccepted") : tPartners("invitationDeclined"));
    } catch {
      toast.error(t("pleaseTryAgain"));
    }
  };

  // Auto-redirect to waiting room if user has a pending session
  useEffect(() => {
    if (isWaiting && sessionId && sessionStartTime) {
      const now = new Date();
      const startTime = new Date(sessionStartTime);

      if (startTime > now) {
        router.push(`/session/${sessionId}/waiting`);
      } else {
        router.push(`/session/${sessionId}`);
      }
    }
  }, [isWaiting, sessionId, sessionStartTime, router]);

  const handleJoinSlot = async (
    slotTime: string,
    mode: "forced_audio" | "quiet",
    topic?: string
  ) => {
    try {
      setIsMatching(true);
      setMatchingSlot(slotTime);

      const data = await api.post<{
        session: { id: string; start_time: string; mode: string };
        livekit_token: string;
        wait_minutes: number;
        is_immediate: boolean;
      }>("/sessions/quick-match", {
        filters: { mode, topic: topic || undefined },
        target_slot_time: slotTime,
      });

      // In debug mode, override start time
      const startTime = debugMode
        ? new Date(Date.now() + DEBUG_WAIT_MINUTES * 60 * 1000)
        : new Date(data.session.start_time);
      const waitMinutes = debugMode ? DEBUG_WAIT_MINUTES : data.wait_minutes;

      setWaitingRoom(startTime, waitMinutes, data.is_immediate);
      setQuietMode(mode === "quiet");
      useSessionStore.setState({ sessionId: data.session.id });

      const livekitUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL;
      if (livekitUrl && data.livekit_token) {
        setLiveKitConnection(data.livekit_token, livekitUrl);
      }

      toast.success(debugMode ? "Debug Match!" : t("matchFound"), {
        description: debugMode
          ? `Debug mode: Session starts in ${DEBUG_WAIT_MINUTES} minutes`
          : data.is_immediate
            ? t("sessionStartingNow")
            : t("sessionStartsIn", { minutes: data.wait_minutes }),
      });

      router.push(`/session/${data.session.id}/waiting`);
    } catch (error: unknown) {
      // Handle 409 Conflict - user already has a session
      if (error instanceof ApiError && error.status === 409) {
        try {
          const detail = JSON.parse(error.message);
          if (detail.detail?.existing_session_id) {
            const existingSessionId = detail.detail.existing_session_id;
            const startTimeStr = detail.detail.start_time;

            if (startTimeStr) {
              const sessionStart = new Date(startTimeStr);
              const now = new Date();

              setWaitingRoom(sessionStart, 0, false);
              useSessionStore.setState({ sessionId: existingSessionId });

              if (sessionStart <= now) {
                toast.info(t("rejoiningSession"), {
                  description: t("sessionAlreadyStarted"),
                });
                router.push(`/session/${existingSessionId}`);
              } else {
                toast.info(t("alreadyHaveSession"), {
                  description: t("redirectingToWaiting"),
                });
                router.push(`/session/${existingSessionId}/waiting`);
              }
              return;
            }
          }
        } catch {
          // JSON parse failed, fall through
        }
      }

      // Handle 402 - insufficient credits
      if (error instanceof ApiError && error.status === 402) {
        useCreditsStore.setState({ balance: 0 });
        openModal("upgrade");
        return;
      }

      console.error("Quick match failed:", error);
      const errorMessage =
        error instanceof Error
          ? error.message
          : typeof error === "object" && error !== null && "detail" in error
            ? String((error as { detail: unknown }).detail)
            : t("pleaseTryAgain");
      toast.error(t("failedToJoinTable"), { description: errorMessage });
    } finally {
      setIsMatching(false);
      setMatchingSlot(null);
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

        {/* Pending invitations */}
        {pendingInvitations.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <Users2 className="h-4 w-4 text-accent" />
              {tPartners("tabs.invitations")} ({pendingInvitations.length})
            </div>
            {pendingInvitations.map((inv) => (
              <InvitationAlert
                key={inv.invitation_id}
                invitation={inv}
                onRespond={handleInvitationRespond}
              />
            ))}
          </div>
        )}

        {/* Zero credits alert */}
        {credits === 0 && <ZeroCreditCard onUpgradeClick={() => openModal("upgrade")} />}

        {/* Find Table Hero — primary action */}
        <FindTableHero
          onJoinSlot={handleJoinSlot}
          isMatching={isMatching}
          matchingSlot={matchingSlot}
          credits={credits}
          hasPendingRatings={hasPendingRatings}
          initialSlots={initialSlots}
        />

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

        {/* Weekly streak */}
        {weeklyStreak && (
          <StreakProgressBar
            sessionCount={weeklyStreak.session_count}
            nextBonusAt={weeklyStreak.next_bonus_at}
            bonus3Awarded={weeklyStreak.bonus_3_awarded}
            bonus5Awarded={weeklyStreak.bonus_5_awarded}
          />
        )}

        {/* Quick links */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/diary")}
            className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <BookOpen className="h-4 w-4" />
            {t("viewDiary")}
          </button>
          <span className="text-border">|</span>
          <button
            onClick={() => openModal("upgrade")}
            className="flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <Coins className="h-4 w-4" />
            {t("getMoreCredits")}
          </button>
        </div>
      </div>

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
                Click &quot;Join&quot; on any time slot to test the flow.
              </p>
            </div>
          ) : (
            <button
              onClick={() => setDebugMode(true)}
              className="p-2 bg-muted hover:bg-warning text-muted-foreground hover:text-warning-foreground rounded-full shadow-lg transition-colors"
              title="Enable Debug Mode (1-min sessions)"
            >
              <Bug className="h-5 w-5" />
            </button>
          )}
        </div>
      )}
    </AppShell>
  );
}
