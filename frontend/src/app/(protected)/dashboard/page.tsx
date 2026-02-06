"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useCreditsStore, useUserStore } from "@/stores";
import { useSessionStore } from "@/stores/session-store";
import { api, ApiError } from "@/lib/api/client";
import { AppShell } from "@/components/layout";
import { StatCard } from "@/components/ui/stat-card";
import { ReliabilityBadge } from "@/components/ui/reliability-badge";
import { Clock, Flame, Coins, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function DashboardPage() {
  const router = useRouter();
  const user = useUserStore((state) => state.user);
  const credits = useCreditsStore((state) => state.balance);
  const { isWaiting, sessionId, sessionStartTime, setWaitingRoom } = useSessionStore();
  const [isMatching, setIsMatching] = useState(false);

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

  const handleQuickMatch = async () => {
    try {
      setIsMatching(true);

      // Use api client to call FastAPI backend (not Next.js /api route)
      const data = await api.post<{
        session: { id: string; start_time: string };
        wait_minutes: number;
        is_immediate: boolean;
      }>("/sessions/quick-match", {});

      // Update session store with waiting room state
      setWaitingRoom(new Date(data.session.start_time), data.wait_minutes, data.is_immediate);

      // Store sessionId for redirect
      useSessionStore.setState({ sessionId: data.session.id });

      // Show success toast
      toast.success("Match found!", {
        description: data.is_immediate
          ? "Session starting now!"
          : `Session starts in ${data.wait_minutes} minutes`,
      });

      // Redirect to waiting room
      router.push(`/session/${data.session.id}/waiting`);
    } catch (error: unknown) {
      console.error("Quick match failed:", error);

      // Handle 409 Conflict - user already has a session
      if (error instanceof ApiError && error.status === 409) {
        try {
          const detail = JSON.parse(error.message);
          if (detail.detail?.existing_session_id) {
            const sessionId = detail.detail.existing_session_id;
            const startTime = detail.detail.start_time;

            // Update session store with existing session
            if (startTime) {
              setWaitingRoom(new Date(startTime), 0, false);
              useSessionStore.setState({ sessionId });
            }

            toast.info("You already have a session!", {
              description: "Redirecting to your waiting room...",
            });

            router.push(`/session/${sessionId}/waiting`);
            return;
          }
        } catch {
          // JSON parse failed, fall through to generic error
        }
      }

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
              onClick={handleQuickMatch}
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
    </AppShell>
  );
}
