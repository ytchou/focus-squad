"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, Clock, Sparkles, Users, Home, Star, Loader2 } from "lucide-react";
import { useSessionStore } from "@/stores/session-store";
import { api } from "@/lib/api/client";

interface SessionSummary {
  focus_minutes: number;
  essence_earned: boolean;
  tablemate_count: number;
  phases_completed: number;
  total_phases: number;
  mode: string;
  topic: string | null;
}

export default function SessionEndPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const { leaveSession } = useSessionStore();

  const [showRatingPrompt, setShowRatingPrompt] = useState(true);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch session summary
  useEffect(() => {
    async function fetchSummary() {
      try {
        const data = await api.get<SessionSummary>(`/sessions/${sessionId}/summary`);
        setSummary(data);
      } catch (err) {
        console.error("Failed to fetch session summary:", err);
        // Use fallback defaults
        setSummary({
          focus_minutes: 0,
          essence_earned: false,
          tablemate_count: 0,
          phases_completed: 0,
          total_phases: 5,
          mode: "forced_audio",
          topic: null,
        });
      } finally {
        setLoading(false);
      }
    }
    fetchSummary();
  }, [sessionId]);

  // Clean up session state on unmount
  useEffect(() => {
    return () => {
      leaveSession();
    };
  }, [leaveSession]);

  const handleReturnHome = () => {
    leaveSession();
    router.push("/dashboard");
  };

  const handleRateTablemates = () => {
    // Rating UI is Phase 3 - for now just dismiss the prompt
    setShowRatingPrompt(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading session summary...</p>
        </div>
      </div>
    );
  }

  const focusMinutes = summary?.focus_minutes ?? 0;
  const essenceEarned = summary?.essence_earned ?? false;
  const tablemateCount = summary?.tablemate_count ?? 0;
  const phasesCompleted = summary?.phases_completed ?? 0;
  const totalPhases = summary?.total_phases ?? 5;
  const mode = summary?.mode ?? "forced_audio";
  const modeLabel = mode === "forced_audio" ? "Forced Audio" : "Quiet Mode";

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Success Card */}
        <Card>
          <CardHeader className="text-center pb-2">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-success/20">
              <CheckCircle className="h-10 w-10 text-success" />
            </div>
            <CardTitle className="text-2xl font-bold">Session Complete!</CardTitle>
            <CardDescription>Great focus session. Here&apos;s your summary.</CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-4">
              <StatCard
                icon={<Clock className="h-5 w-5 text-primary" />}
                label="Focus Time"
                value={`${focusMinutes} min`}
              />
              <StatCard
                icon={<Sparkles className="h-5 w-5 text-accent" />}
                label="Essence Earned"
                value={essenceEarned ? "+1" : "--"}
              />
              <StatCard
                icon={<Users className="h-5 w-5 text-muted-foreground" />}
                label="Tablemates"
                value={String(tablemateCount)}
              />
              <StatCard
                icon={<CheckCircle className="h-5 w-5 text-success" />}
                label="Phases"
                value={`${phasesCompleted}/${totalPhases}`}
              />
            </div>

            {/* Session Details */}
            <div className="bg-muted rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Session ID</span>
                <code className="text-xs bg-background px-2 py-1 rounded">
                  {sessionId.slice(0, 8)}...
                </code>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Duration</span>
                <span className="font-medium">55 minutes</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Mode</span>
                <Badge variant="outline">{modeLabel}</Badge>
              </div>
              {summary?.topic && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Topic</span>
                  <span className="font-medium">{summary.topic}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Rating Prompt (Phase 3 feature - placeholder) */}
        {showRatingPrompt && (
          <Card className="border-accent/50">
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/20 flex-shrink-0">
                  <Star className="h-5 w-5 text-accent" />
                </div>
                <div className="flex-1 space-y-2">
                  <h3 className="font-medium">Rate your tablemates</h3>
                  <p className="text-sm text-muted-foreground">
                    Help build trust in the community by rating whether your tablemates were focused
                    and present.
                  </p>
                  <div className="flex gap-2 pt-2">
                    <Button size="sm" onClick={handleRateTablemates}>
                      Rate Now
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => setShowRatingPrompt(false)}>
                      Skip
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Return Home Button */}
        <Button size="lg" className="w-full" onClick={handleReturnHome}>
          <Home className="h-4 w-4 mr-2" />
          Return to Dashboard
        </Button>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="bg-card rounded-lg p-4 border border-border">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <p className="text-xl font-bold">{value}</p>
    </div>
  );
}
