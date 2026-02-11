"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Search, Calendar, List } from "lucide-react";
import { cn } from "@/lib/utils";

interface DiaryHeaderProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  viewMode: "timeline" | "calendar";
  onViewModeChange: (mode: "timeline" | "calendar") => void;
  dateRange: { from?: string; to?: string };
  onDateRangeChange: (range: { from?: string; to?: string }) => void;
}

export function DiaryHeader({
  searchQuery,
  onSearchChange,
  viewMode,
  onViewModeChange,
  dateRange,
  onDateRangeChange,
}: DiaryHeaderProps) {
  const t = useTranslations("diary");
  const [showDatePicker, setShowDatePicker] = useState(false);
  const hasDateFilter = dateRange.from || dateRange.to;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-foreground">{t("title")}</h1>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Search bar */}
        <div className="relative max-w-md flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder={t("searchPlaceholder")}
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface py-2 pl-10 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Date range toggle */}
          <button
            type="button"
            onClick={() => setShowDatePicker(!showDatePicker)}
            className={cn(
              "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              hasDateFilter
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80"
            )}
          >
            <Calendar className="h-4 w-4" />
            {t("dateRange")}
          </button>

          {/* View toggle */}
          <div className="flex rounded-lg bg-muted p-1">
            <button
              type="button"
              onClick={() => onViewModeChange("timeline")}
              className={cn(
                "flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium transition-colors",
                viewMode === "timeline"
                  ? "bg-surface text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <List className="h-4 w-4" />
              {t("timeline")}
            </button>
            <button
              type="button"
              onClick={() => onViewModeChange("calendar")}
              className={cn(
                "flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium transition-colors",
                viewMode === "calendar"
                  ? "bg-surface text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Calendar className="h-4 w-4" />
              {t("calendar")}
            </button>
          </div>
        </div>
      </div>

      {/* Date range picker */}
      {showDatePicker && (
        <div className="rounded-lg border border-border bg-card p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium text-foreground">{t("dateFrom")}</label>
              <input
                type="date"
                value={dateRange.from || ""}
                onChange={(e) =>
                  onDateRangeChange({ ...dateRange, from: e.target.value || undefined })
                }
                className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">{t("dateTo")}</label>
              <input
                type="date"
                value={dateRange.to || ""}
                onChange={(e) =>
                  onDateRangeChange({ ...dateRange, to: e.target.value || undefined })
                }
                className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm"
              />
            </div>
          </div>
          {hasDateFilter && (
            <button
              type="button"
              onClick={() => onDateRangeChange({ from: undefined, to: undefined })}
              className="mt-3 text-sm text-muted-foreground hover:text-foreground"
            >
              {t("clearDates")}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
