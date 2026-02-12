"use client";

import { useTranslations } from "next-intl";
import { AppShell } from "@/components/layout";
import { Construction } from "lucide-react";

export default function SchedulesPage() {
  const t = useTranslations("schedule");
  const tCommon = useTranslations("common");

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>
          <p className="mt-1 text-muted-foreground">{t("subtitle")}</p>
        </div>

        <div className="rounded-2xl bg-card p-12 shadow-sm flex flex-col items-center justify-center text-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <Construction className="h-8 w-8 text-muted-foreground" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-foreground">{tCommon("comingSoon")}</h2>
            <p className="mt-1 text-sm text-muted-foreground">{t("unlimited_only")}</p>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
