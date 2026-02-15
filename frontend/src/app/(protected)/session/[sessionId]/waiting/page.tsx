"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useSessionStore } from "@/stores/session-store";
import { api } from "@/lib/api/client";
import { trackWaitingRoomEntered, trackWaitingRoomAbandoned } from "@/lib/posthog/events";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Volume2, Clock, Info } from "lucide-react";

export default function WaitingRoomPage() {
  const router = useRouter();
  const params = useParams();
  const t = useTranslations("waitingRoom");
  const sessionId = params.sessionId as string;

  const { sessionStartTime, isWaiting, waitMinutes, clearWaitingRoom } = useSessionStore();

  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [showGetReady, setShowGetReady] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);
  const hasRedirected = useRef(false);
  const initialTimeRef = useRef<number | null>(null);

  // Calculate time remaining and handle countdown
  useEffect(() => {
    if (!sessionStartTime) {
      if (!hasRedirected.current) {
        hasRedirected.current = true;
        router.push("/dashboard");
      }
      return;
    }

    const startTime = new Date(sessionStartTime);

    const updateCountdown = () => {
      if (hasRedirected.current) return;

      const now = new Date();
      const remaining = Math.max(0, Math.floor((startTime.getTime() - now.getTime()) / 1000));

      // Auto-redirect at T-0 (before setting state to avoid re-render cascade)
      if (remaining === 0) {
        hasRedirected.current = true;
        clearInterval(interval);

        clearWaitingRoom();
        router.push(`/session/${sessionId}`);
        return;
      }

      setTimeRemaining(remaining);

      // Show "Get Ready!" at T-10s
      if (remaining <= 10) {
        setShowGetReady(true);
      }
    };

    // Update every second
    const interval = setInterval(updateCountdown, 1000);

    // Initial update (after interval is defined so clearInterval works)
    updateCountdown();

    return () => clearInterval(interval);
  }, [sessionStartTime, sessionId, router, clearWaitingRoom]);

  // Track initial time remaining for abandon calculation
  useEffect(() => {
    if (timeRemaining > 0 && initialTimeRef.current === null) {
      initialTimeRef.current = timeRemaining;
    }
  }, [timeRemaining]);

  // Track waiting room entered
  useEffect(() => {
    trackWaitingRoomEntered(sessionId, waitMinutes ?? 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      const waitedSeconds = (initialTimeRef.current ?? 0) - timeRemaining;
      trackWaitingRoomAbandoned(sessionId, waitedSeconds, timeRemaining);

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
          <CardTitle className="text-3xl font-bold">{t("title")}</CardTitle>
          <CardDescription>
            {t("sessionStartsAt", { time: formatStartTime(sessionStartTime) })}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Countdown Timer */}
          <div className="text-center">
            <div className="flex items-center justify-center gap-2 mb-2">
              <Clock className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">{t("timeUntilStart")}</span>
            </div>
            <div className="text-6xl font-bold tracking-tight text-primary">
              {formatTime(timeRemaining)}
            </div>
          </div>

          {/* Get Ready Warning */}
          {showGetReady && (
            <div className="animate-pulse">
              <Badge className="w-full py-3 text-lg justify-center bg-warning text-warning-foreground hover:bg-warning/90">
                {t("getReady")}
              </Badge>
            </div>
          )}

          {/* Audio Privacy Warning */}
          <div className="bg-muted rounded-lg p-4 space-y-2">
            <div className="flex items-start gap-3">
              <Volume2 className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <p className="text-sm font-medium">{t("audioConnectTitle")}</p>
                <p className="text-xs text-muted-foreground">{t("audioConnectDesc")}</p>
              </div>
            </div>
          </div>

          {/* No Refund Notice */}
          <div className="bg-muted rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-muted-foreground mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <p className="text-sm font-medium">{t("noRefundTitle")}</p>
                <p className="text-xs text-muted-foreground">{t("noRefundDesc")}</p>
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
            {isLeaving ? t("leaving") : t("leaveNoRefund")}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
