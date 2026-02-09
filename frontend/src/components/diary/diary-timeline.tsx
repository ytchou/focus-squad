"use client";

import { Loader2 } from "lucide-react";
import { DiaryEntryCard } from "./diary-entry-card";
import type { DiaryEntry } from "@/lib/api/client";

interface DiaryTimelineProps {
  entries: DiaryEntry[];
  isLoading: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
  onSaveNote: (sessionId: string, note: string, tags: string[]) => Promise<void>;
}

export function DiaryTimeline({
  entries,
  isLoading,
  hasMore,
  onLoadMore,
  onSaveNote,
}: DiaryTimelineProps) {
  if (isLoading && entries.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="rounded-2xl border border-border bg-card p-12 text-center">
        <p className="mb-2 text-lg font-medium text-foreground">No sessions yet</p>
        <p className="text-sm text-muted-foreground">
          Join your first table to start building your focus journey!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {entries.map((entry) => (
        <DiaryEntryCard key={entry.session_id} entry={entry} onSaveNote={onSaveNote} />
      ))}

      {hasMore && (
        <button
          type="button"
          onClick={onLoadMore}
          disabled={isLoading}
          className="w-full rounded-lg border border-border py-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted disabled:opacity-50"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading...
            </span>
          ) : (
            "Load More"
          )}
        </button>
      )}
    </div>
  );
}
