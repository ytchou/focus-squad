"use client";

import { useEffect } from "react";
import { useRatingStore } from "@/stores";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ThumbsUp, ThumbsDown, History } from "lucide-react";
import { cn } from "@/lib/utils";

export function RatingHistoryCard() {
  const { ratingHistory, isLoadingHistory, fetchRatingHistory } = useRatingStore();

  useEffect(() => {
    fetchRatingHistory();
  }, [fetchRatingHistory]);

  if (isLoadingHistory && !ratingHistory) {
    return (
      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <History className="h-5 w-5 text-muted-foreground" />
            Rating History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
            <div className="h-8 w-full animate-pulse rounded-full bg-muted" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const summary = ratingHistory?.summary;
  const items = ratingHistory?.items ?? [];
  const total = ratingHistory?.total ?? 0;
  const hasMore = items.length < total;

  if (summary && summary.total_received === 0) {
    return (
      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <History className="h-5 w-5 text-muted-foreground" />
            Rating History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No ratings yet. Complete a session and your tablemates will rate you!
          </p>
        </CardContent>
      </Card>
    );
  }

  const greenPct = summary?.green_percentage ?? 0;
  const redPct = summary ? 100 - greenPct : 0;

  return (
    <Card className="rounded-2xl shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <History className="h-5 w-5 text-muted-foreground" />
          Rating History
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary bar */}
        {summary && summary.total_received > 0 && (
          <div className="space-y-2">
            <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
              {greenPct > 0 && (
                <div
                  className="bg-success transition-all duration-500"
                  style={{ width: `${greenPct}%` }}
                />
              )}
              {redPct > 0 && (
                <div
                  className="bg-destructive transition-all duration-500"
                  style={{ width: `${redPct}%` }}
                />
              )}
            </div>
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1 text-success">
                  <ThumbsUp className="h-3.5 w-3.5" />
                  {summary.green_count} Green
                </span>
                <span className="flex items-center gap-1 text-destructive">
                  <ThumbsDown className="h-3.5 w-3.5" />
                  {summary.red_count} Red
                </span>
              </div>
              <span className="text-muted-foreground">{summary.total_received} total</span>
            </div>
          </div>
        )}

        {/* Recent ratings list */}
        {items.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">Recent</p>
            <ul className="space-y-1.5">
              {items.map((item) => (
                <li
                  key={item.id}
                  className="flex items-center justify-between rounded-lg px-3 py-2 bg-muted/50"
                >
                  <span
                    className={cn(
                      "flex items-center gap-2 text-sm font-medium",
                      item.rating === "green" ? "text-success" : "text-destructive"
                    )}
                  >
                    {item.rating === "green" ? (
                      <ThumbsUp className="h-3.5 w-3.5" />
                    ) : (
                      <ThumbsDown className="h-3.5 w-3.5" />
                    )}
                    {item.rating === "green" ? "Green" : "Red"}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(item.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Load more */}
        {hasMore && (
          <button
            onClick={() => {
              const nextPage = (ratingHistory?.page ?? 1) + 1;
              fetchRatingHistory(nextPage);
            }}
            disabled={isLoadingHistory}
            className="w-full rounded-lg border border-border py-2 text-sm text-muted-foreground transition-colors hover:bg-muted disabled:opacity-50"
          >
            {isLoadingHistory ? "Loading..." : "Load More"}
          </button>
        )}
      </CardContent>
    </Card>
  );
}
