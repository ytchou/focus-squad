"use client";

import { useTranslations } from "next-intl";
import { useCreditsStore, useUserStore } from "@/stores";
import { AppShell } from "@/components/layout";
import { StatCard } from "@/components/ui/stat-card";
import { ReliabilityBadge } from "@/components/ui/reliability-badge";
import { Clock, Flame, Coins } from "lucide-react";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  // User and credits are loaded by useAuth's onAuthStateChange listener
  // which fires on INITIAL_SESSION (page load) and SIGNED_IN (login)
  const user = useUserStore((state) => state.user);
  const credits = useCreditsStore((state) => state.balance);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Welcome section */}
        <div className="rounded-2xl bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-foreground">
                {t("welcomeBack", {
                  name: user?.display_name ?? user?.username ?? "Friend",
                })}
              </h1>
              <p className="mt-1 text-muted-foreground">{t("welcomeSubtitle")}</p>
            </div>
            {user && <ReliabilityBadge score={user.reliability_score} />}
          </div>
        </div>

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
            <button className="flex items-center gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:bg-muted">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent/20 text-accent">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-foreground">{t("joinTable")}</p>
                <p className="text-sm text-muted-foreground">{t("joinStudySession")}</p>
              </div>
            </button>
            <button className="flex items-center gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:bg-muted">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/20 text-success">
                <Flame className="h-5 w-5" />
              </div>
              <div>
                <p className="font-medium text-foreground">{t("viewDiary")}</p>
                <p className="text-sm text-muted-foreground">{t("growthJournal")}</p>
              </div>
            </button>
            <button className="flex items-center gap-3 rounded-xl border border-border p-4 text-left transition-colors hover:bg-muted">
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
    </AppShell>
  );
}
