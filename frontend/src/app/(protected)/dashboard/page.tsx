"use client";

import { useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useCreditsStore, useUserStore } from "@/stores";
import { AppShell } from "@/components/layout";
import { StatCard } from "@/components/ui/stat-card";
import { ReliabilityBadge } from "@/components/ui/reliability-badge";
import { Clock, Flame, Coins } from "lucide-react";

export default function DashboardPage() {
  const { refreshProfile } = useAuth();
  const user = useUserStore((state) => state.user);
  const credits = useCreditsStore((state) => state.balance);

  useEffect(() => {
    refreshProfile();
  }, [refreshProfile]);

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
              <p className="mt-1 text-muted-foreground">
                Ready for your next focus session?
              </p>
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
          <StatCard
            title="Credits"
            value={credits}
            subtitle="available this week"
            icon={Coins}
          />
        </div>

        {/* Quick actions */}
        <div className="rounded-2xl bg-card p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-foreground">
            Quick Actions
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <button className="flex items-center gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:bg-muted">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/20 text-accent">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-foreground">Find a Table</p>
                <p className="text-sm text-muted-foreground">Join a study session</p>
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
