"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2, Camera } from "lucide-react";
import { useGamificationStore } from "@/stores";
import { TimelineCard } from "@/components/room/timeline-card";
import { MilestoneShareModal } from "@/components/room/milestone-share-modal";

export default function TimelinePage() {
  const t = useTranslations("timeline");
  const router = useRouter();
  const snapshots = useGamificationStore((s) => s.snapshots);
  const timelineTotal = useGamificationStore((s) => s.timelineTotal);
  const timelinePage = useGamificationStore((s) => s.timelinePage);
  const isTimelineLoading = useGamificationStore((s) => s.isTimelineLoading);
  const fetchTimeline = useGamificationStore((s) => s.fetchTimeline);

  useEffect(() => {
    fetchTimeline(1);
  }, [fetchTimeline]);

  const hasMore = snapshots.length < timelineTotal;

  return (
    <AppShell>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => router.push("/room")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-xl font-semibold text-foreground">{t("title")}</h1>
            <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
          </div>
        </div>

        {/* Timeline grid */}
        {snapshots.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {snapshots.map((snapshot) => (
              <TimelineCard key={snapshot.id} snapshot={snapshot} />
            ))}
          </div>
        ) : (
          !isTimelineLoading && (
            <div className="text-center py-12">
              <Camera className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
              <p className="text-muted-foreground text-sm">{t("empty")}</p>
              <p className="text-muted-foreground text-xs mt-1">{t("emptyHint")}</p>
            </div>
          )
        )}

        {/* Load more */}
        {hasMore && (
          <div className="text-center">
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchTimeline(timelinePage + 1)}
              disabled={isTimelineLoading}
            >
              {isTimelineLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : t("loadMore")}
            </Button>
          </div>
        )}

        {/* Loading state */}
        {isTimelineLoading && snapshots.length === 0 && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>

      <MilestoneShareModal />
    </AppShell>
  );
}
