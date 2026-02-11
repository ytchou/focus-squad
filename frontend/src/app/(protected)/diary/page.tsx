"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { AppShell } from "@/components/layout";
import { DiaryHeader } from "@/components/diary/diary-header";
import { DiaryTimeline } from "@/components/diary/diary-timeline";
import { DiaryCalendar } from "@/components/diary/diary-calendar";
import { api, type DiaryEntry, type DiaryResponse } from "@/lib/api/client";
import { useDebounce } from "@/hooks/use-debounce";
import { toast } from "sonner";

type ViewMode = "timeline" | "calendar";

export default function DiaryPage() {
  const t = useTranslations("diary");
  const searchParams = useSearchParams();

  const initialSearch = searchParams.get("search") || "";
  const initialView = (searchParams.get("view") as ViewMode) || "timeline";

  const [entries, setEntries] = useState<DiaryEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState(initialSearch);
  const [viewMode, setViewMode] = useState<ViewMode>(initialView);
  const [dateRange, setDateRange] = useState<{ from?: string; to?: string }>({});
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const debouncedSearch = useDebounce(searchQuery, 300);

  const fetchEntries = useCallback(
    async (targetPage: number, append: boolean) => {
      try {
        setIsLoading(true);
        const params = new URLSearchParams();
        params.set("page", targetPage.toString());
        params.set("per_page", "20");
        if (debouncedSearch) params.set("search", debouncedSearch);
        if (dateRange.from) params.set("date_from", dateRange.from);
        if (dateRange.to) params.set("date_to", dateRange.to);

        const response = await api.get<DiaryResponse>(`/sessions/diary?${params}`);

        if (append) {
          setEntries((prev) => [...prev, ...response.items]);
        } else {
          setEntries(response.items);
        }
        setTotal(response.total);
      } catch (error) {
        console.error("Failed to fetch diary entries:", error);
        toast.error(t("failedToLoadEntries"));
      } finally {
        setIsLoading(false);
      }
    },
    [debouncedSearch, dateRange.from, dateRange.to, t]
  );

  // Initial load + refetch on filter change
  useEffect(() => {
    setPage(1);
    fetchEntries(1, false);
  }, [fetchEntries]);

  // Update URL params
  useEffect(() => {
    const params = new URLSearchParams();
    if (searchQuery) params.set("search", searchQuery);
    if (viewMode !== "timeline") params.set("view", viewMode);
    const newUrl = params.toString() ? `/diary?${params}` : "/diary";
    window.history.replaceState(null, "", newUrl);
  }, [searchQuery, viewMode]);

  const handleSaveNote = async (sessionId: string, note: string, tags: string[]) => {
    try {
      await api.post(`/sessions/diary/${sessionId}/note`, { note, tags });
      setEntries((prev) =>
        prev.map((entry) => (entry.session_id === sessionId ? { ...entry, note, tags } : entry))
      );
      toast.success(t("noteSaved"));
    } catch (error) {
      console.error("Failed to save note:", error);
      toast.error(t("failedToSaveNote"));
      throw error;
    }
  };

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchEntries(nextPage, true);
  };

  const hasMore = entries.length < total;

  return (
    <AppShell>
      <div className="space-y-6">
        <DiaryHeader
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          dateRange={dateRange}
          onDateRangeChange={setDateRange}
        />

        {viewMode === "timeline" ? (
          <DiaryTimeline
            entries={entries}
            isLoading={isLoading}
            hasMore={hasMore}
            onLoadMore={handleLoadMore}
            onSaveNote={handleSaveNote}
          />
        ) : (
          <DiaryCalendar entries={entries} onSaveNote={handleSaveNote} />
        )}
      </div>
    </AppShell>
  );
}
