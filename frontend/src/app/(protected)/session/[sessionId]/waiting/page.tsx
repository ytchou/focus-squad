"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useSessionStore } from "@/stores/session-store";
import { api } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Volume2, Clock, Info } from "lucide-react";

export default function WaitingRoomPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const { sessionStartTime, isWaiting, clearWaitingRoom } = useSessionStore();

  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [showGetReady, setShowGetReady] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  // Track "waiting_room_resumed" event on mount (page reload)
  // We intentionally only run this once on mount to track page reloads, not re-renders
  useEffect(() => {
    if (sessionId && sessionStartTime) {
      const minutesBeforeStart = Math.floor(
        (new Date(sessionStartTime).getTime() - Date.now()) / 60000
      );

      // Fire-and-forget analytics tracking
      api
        .post("/analytics/track", {
          event_type: "waiting_room_resumed",
          session_id: sessionId,
          metadata: {
            minutes_before_start: minutesBeforeStart,
          },
        })
        .catch(() => {}); // Ignore errors
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount

  // Calculate time remaining and handle countdown
  useEffect(() => {
    if (!sessionStartTime) {
      // No session start time, redirect to dashboard
      router.push("/dashboard");
      return;
    }

    const startTime = new Date(sessionStartTime);

    const updateCountdown = () => {
      const now = new Date();
      const remaining = Math.max(0, Math.floor((startTime.getTime() - now.getTime()) / 1000));
      setTimeRemaining(remaining);

      // Show "Get Ready!" at T-10s
      if (remaining <= 10 && remaining > 0) {
        setShowGetReady(true);
      }

      // Auto-redirect at T-0
      if (remaining === 0) {
        clearInterval(interval);

        // Track successful join
        api
          .post("/analytics/track", {
            event_type: "session_joined_from_waiting_room",
            session_id: sessionId,
            metadata: {},
          })
          .catch(() => {});

        clearWaitingRoom();
        router.push(`/session/${sessionId}`);
      }
    };

    // Update every second
    const interval = setInterval(updateCountdown, 1000);

    // Initial update (after interval is defined so clearInterval works)
    updateCountdown();

    return () => clearInterval(interval);
  }, [sessionStartTime, sessionId, router, clearWaitingRoom]);

  // Format time as MM:SS
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  // Handle leave button
  const handleLeave = async () => {
    setIsLeaving(true);
    try {
      // Track abandonment (fire-and-forget)
      const minutesBeforeStart = sessionStartTime
        ? Math.floor((new Date(sessionStartTime).getTime() - Date.now()) / 60000)
        : 0;

      api
        .post("/analytics/track", {
          event_type: "waiting_room_abandoned",
          session_id: sessionId,
          metadata: {
            minutes_before_start: minutesBeforeStart,
            reason: "user_clicked_leave",
          },
        })
        .catch(() => {});

      // Call leave session API (FastAPI backend)
      await api.post(`/sessions/${sessionId}/leave`);

      // Clear waiting room state
      clearWaitingRoom();

      // Redirect to dashboard
      router.push("/dashboard");
    } catch (error) {
      console.error("Failed to leave session:", error);
      setIsLeaving(false);
    }
  };

  // Format start time for display
  const formatStartTime = (date: Date | null): string => {
    if (!date) return "";
    return new Date(date).toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  };

  if (!isWaiting || !sessionStartTime) {
    return null; // Will redirect in useEffect
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold">Waiting Room</CardTitle>
          <CardDescription>Session starts at {formatStartTime(sessionStartTime)}</CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Countdown Timer */}
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Clock className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Time until session starts</span>
            </div>
            <div className="text-6xl font-bold tracking-tight text-primary">
              {formatTime(timeRemaining)}
            </div>
          </div>

          {/* Get Ready Warning */}
          {showGetReady && (
            <div className="animate-pulse">
              <Badge className="w-full py-3 text-lg justify-center bg-warning text-warning-foreground hover:bg-warning/90">
                Get Ready! Session starting soon...
              </Badge>
            </div>
          )}

          {/* Audio Privacy Warning */}
          <div className="bg-muted rounded-lg p-4 space-y-2">
            <div className="flex items-start gap-3">
              <Volume2 className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <p className="text-sm font-medium">Audio will connect automatically</p>
                <p className="text-xs text-muted-foreground">
                  Your microphone will be unmuted when the session begins. Make sure you are in a
                  quiet space and ready to focus.
                </p>
              </div>
            </div>
          </div>

          {/* No Refund Notice */}
          <div className="bg-muted rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-muted-foreground mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <p className="text-sm font-medium">No refunds for early departure</p>
                <p className="text-xs text-muted-foreground">
                  If you leave now or miss the session, your credit will not be refunded. Please
                  only leave if absolutely necessary.
                </p>
              </div>
            </div>
          </div>

          {/* Leave Button */}
          <Button
            variant="outline"
            size="lg"
            className="w-full"
            onClick={handleLeave}
            disabled={isLeaving}
          >
            {isLeaving ? "Leaving..." : "Leave Session (No Refund)"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
