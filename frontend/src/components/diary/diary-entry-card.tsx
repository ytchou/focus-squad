"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Target,
  Coffee,
  MessageCircle,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { DiaryJournalEditor } from "./diary-journal-editor";
import type { DiaryEntry } from "@/lib/api/client";

interface DiaryEntryCardProps {
  entry: DiaryEntry;
  onSaveNote: (sessionId: string, note: string, tags: string[]) => Promise<void>;
}

const PHASE_CONFIG = {
  setup: {
    labelKey: "goalTag" as const,
    icon: Target,
    className: "bg-primary/10 border-primary/20 text-primary",
  },
  break: {
    labelKey: "checkInLabel" as const,
    icon: Coffee,
    className: "bg-success/10 border-success/20 text-success",
  },
  social: {
    labelKey: "afterthoughtsLabel" as const,
    icon: MessageCircle,
    className: "bg-accent/10 border-accent/20 text-accent",
  },
} as const;

export function DiaryEntryCard({ entry, onSaveNote }: DiaryEntryCardProps) {
  const t = useTranslations("diary");
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async (note: string, tags: string[]) => {
    setIsSaving(true);
    try {
      await onSaveNote(entry.session_id, note, tags);
    } finally {
      setIsSaving(false);
    }
  };

  const sessionDate = new Date(entry.session_date);
  const formattedDate = sessionDate.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const formattedTime = sessionDate.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-foreground">
            {entry.session_topic || t("focusSession")}
          </h3>
          <div className="mt-1 flex items-center gap-3 text-sm text-muted-foreground">
            <span>{formattedDate}</span>
            <span>&middot;</span>
            <span>{formattedTime}</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-primary" />
            <span className="font-medium text-foreground">
              {t("min", { minutes: entry.focus_minutes })}
            </span>
          </div>
          {entry.focus_minutes >= 20 && (
            <div className="flex items-center gap-2 text-sm">
              <Sparkles className="h-4 w-4 text-accent" />
              <span className="font-medium text-foreground">{t("essence")}</span>
            </div>
          )}
        </div>
      </div>

      {/* Tags */}
      {entry.tags.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {entry.tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
      )}

      {/* Reflections (collapsible) */}
      {entry.reflections.length > 0 && (
        <div className="mb-4">
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            {entry.reflections.length > 1
              ? t("reflectionCountPlural", { count: entry.reflections.length })
              : t("reflectionCount", { count: entry.reflections.length })}
          </button>

          {isExpanded && (
            <div className="mt-3 space-y-2">
              {entry.reflections.map((reflection) => {
                const config = PHASE_CONFIG[reflection.phase];
                const Icon = config.icon;
                return (
                  <div
                    key={reflection.phase}
                    className={cn("rounded-lg border p-3", config.className)}
                  >
                    <div className="mb-1 flex items-center gap-2">
                      <Icon className="h-3.5 w-3.5" />
                      <span className="text-xs font-medium">{t(config.labelKey)}</span>
                    </div>
                    <p className="pl-5 text-sm leading-relaxed text-foreground/90">
                      {reflection.content}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* No reflections placeholder */}
      {entry.reflections.length === 0 && (
        <p className="mb-4 text-sm text-muted-foreground/60">{t("noReflections")}</p>
      )}

      {/* Journal note display */}
      {entry.note && !isSaving && (
        <div className="mb-4 rounded-lg bg-muted/50 p-4">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">
            {entry.note}
          </p>
        </div>
      )}

      {/* Add/edit note section */}
      <DiaryJournalEditor
        initialNote={entry.note || ""}
        initialTags={entry.tags}
        onSave={handleSave}
        isSaving={isSaving}
      />
    </div>
  );
}
