"use client";

import { useTranslations } from "next-intl";
import { Camera, Star, Users, BookOpen, Sparkles, Flame, Lightbulb, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUIStore } from "@/stores";
import type { RoomSnapshot } from "@/stores/gamification-store";

const MILESTONE_ICONS: Record<string, React.ReactNode> = {
  first_item: <Star className="h-4 w-4" />,
  session_milestone: <Flame className="h-4 w-4" />,
  companion_discovered: <Users className="h-4 w-4" />,
  room_unlocked: <Sparkles className="h-4 w-4" />,
  first_diary: <BookOpen className="h-4 w-4" />,
  diary_streak_7: <Flame className="h-4 w-4" />,
  first_breakthrough: <Lightbulb className="h-4 w-4" />,
};

interface TimelineCardProps {
  snapshot: RoomSnapshot;
}

export function TimelineCard({ snapshot }: TimelineCardProps) {
  const t = useTranslations("timeline");
  const openModal = useUIStore((s) => s.openModal);

  const icon = MILESTONE_ICONS[snapshot.milestone_type] ?? <Camera className="h-4 w-4" />;

  const date = new Date(snapshot.created_at);
  const formattedDate = date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden shadow-soft">
      {/* Snapshot image */}
      <div className="relative aspect-[3/2] bg-muted">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={snapshot.image_url}
          alt={t(`milestone.${snapshot.milestone_type}`)}
          className="w-full h-full object-cover"
        />
      </div>

      {/* Card content */}
      <div className="p-3 space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-6 h-6 rounded-full bg-accent/20 text-accent">
            {icon}
          </span>
          <span className="text-sm font-medium text-foreground">
            {t(`milestone.${snapshot.milestone_type}`)}
          </span>
        </div>

        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span>{formattedDate}</span>
          {snapshot.session_count_at > 0 && (
            <span>{t("sessionCount", { count: snapshot.session_count_at })}</span>
          )}
        </div>

        {snapshot.diary_excerpt && (
          <p className="text-xs text-muted-foreground italic line-clamp-2">
            &ldquo;{snapshot.diary_excerpt}&rdquo;
          </p>
        )}

        <Button
          variant="ghost"
          size="xs"
          className="w-full mt-1"
          onClick={() => openModal("milestoneShare", { snapshot })}
        >
          <Share2 className="h-3.5 w-3.5" />
          {t("share")}
        </Button>
      </div>
    </div>
  );
}
