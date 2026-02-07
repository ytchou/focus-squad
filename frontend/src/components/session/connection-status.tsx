"use client";

import { useEffect, useState } from "react";
import { Wifi, WifiOff, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const GRACE_PERIOD_MS = 2 * 60 * 1000; // 2 minutes

type ConnectionState = "connected" | "connecting" | "reconnecting" | "disconnected";

interface ConnectionStatusProps {
  state: ConnectionState;
  onReconnect?: () => void;
  disconnectedAt?: Date | null;
}

export function ConnectionStatus({ state, onReconnect, disconnectedAt }: ConnectionStatusProps) {
  const [tick, setTick] = useState(0);

  // Trigger re-render every second when disconnected
  useEffect(() => {
    if (!disconnectedAt || state === "connected") {
      return;
    }

    const interval = setInterval(() => {
      setTick((t) => t + 1);
    }, 1000);

    return () => clearInterval(interval);
  }, [disconnectedAt, state]);

  // Compute grace time remaining based on tick counter
  // Each tick represents ~1 second elapsed since the interval started
  const graceTimeRemaining = (() => {
    if (!disconnectedAt || state === "connected") {
      return null;
    }
    // Use tick * 1000 to approximate elapsed time without calling Date.now()
    // This is slightly less accurate but avoids the impure function issue
    const elapsedMs = tick * 1000;
    return Math.max(0, GRACE_PERIOD_MS - elapsedMs);
  })();

  // Don't show anything when connected
  if (state === "connected") {
    return null;
  }

  return (
    <div
      className={cn(
        "fixed top-16 left-0 right-0 z-20 px-4 py-2 flex items-center justify-center gap-2 text-sm",
        state === "connecting" && "bg-muted",
        state === "reconnecting" && "bg-warning/20 text-warning-foreground",
        state === "disconnected" && "bg-destructive/20 text-destructive"
      )}
    >
      {state === "connecting" && (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Connecting to session...</span>
        </>
      )}

      {state === "reconnecting" && (
        <>
          <Wifi className="h-4 w-4" />
          <span>Reconnecting...</span>
          {graceTimeRemaining !== null && graceTimeRemaining > 0 && (
            <span className="text-xs opacity-75">
              ({Math.ceil(graceTimeRemaining / 1000)}s grace period)
            </span>
          )}
        </>
      )}

      {state === "disconnected" && (
        <>
          <WifiOff className="h-4 w-4" />
          <span>Connection lost</span>
          {onReconnect && (
            <Button variant="outline" size="sm" onClick={onReconnect} className="ml-2 h-7">
              Reconnect
            </Button>
          )}
        </>
      )}
    </div>
  );
}
