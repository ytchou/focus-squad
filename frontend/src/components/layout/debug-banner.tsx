"use client";

import { useEffect } from "react";
import { X, Bug } from "lucide-react";
import { useUserStore } from "@/stores/user-store";
import { useDebugBanner } from "@/hooks/use-debug-banner";

export function DebugBanner() {
  const { isDev, isDismissed, setDismissed } = useDebugBanner();
  const user = useUserStore((state) => state.user);

  // Update document title in dev mode
  useEffect(() => {
    if (!isDev) return;

    const originalTitle = document.title;
    if (!originalTitle.startsWith("[DEV]")) {
      document.title = `[DEV] ${originalTitle}`;
    }

    return () => {
      document.title = originalTitle;
    };
  }, [isDev]);

  // Only show in development
  if (!isDev) {
    return null;
  }

  if (isDismissed) {
    return (
      <button
        onClick={() => setDismissed(false)}
        className="fixed top-2 right-2 z-[100] p-1.5 bg-warning/80 text-warning-foreground rounded-full shadow-md hover:bg-warning transition-colors"
        title="Show debug banner"
      >
        <Bug className="h-4 w-4" />
      </button>
    );
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const truncatedUserId = user?.id ? user.id.slice(0, 8) : "not logged in";

  return (
    <>
      {/* Fixed banner at top */}
      <div className="fixed top-0 left-0 right-0 z-[100] bg-warning/95 text-warning-foreground backdrop-blur-sm">
        <div className="flex items-center justify-between px-4 py-1.5 text-xs font-mono">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <Bug className="h-3.5 w-3.5" />
              <span className="font-semibold bg-warning-foreground/10 px-1.5 py-0.5 rounded">
                DEV
              </span>
            </span>
            <span className="text-warning-foreground/80">
              API: <span className="text-warning-foreground">{apiUrl}</span>
            </span>
            <span className="text-warning-foreground/80">
              User: <span className="text-warning-foreground">{truncatedUserId}</span>
            </span>
          </div>
          <button
            onClick={() => setDismissed(true)}
            className="p-1 hover:bg-warning-foreground/10 rounded transition-colors"
            title="Dismiss debug banner"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
      {/* Spacer to push content down */}
      <div className="h-8" aria-hidden="true" />
    </>
  );
}
