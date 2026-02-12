"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle,
  Clock,
  Sparkles,
  Users,
  Home,
  Loader2,
  AlertCircle,
  Star,
  Flag,
  UserPlus,
} from "lucide-react";
import { useSessionStore } from "@/stores/session-store";
import { useRatingStore } from "@/stores/rating-store";
import { RatingCard } from "@/components/session/rating-card";
import { ReportModal } from "@/components/moderation/report-modal";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api/client";
import { usePartnerStore } from "@/stores";
import { AddPartnerButton } from "@/components/partners";
import { toast } from "sonner";

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
  const t = useTranslations("sessionEnd");
  const tRating = useTranslations("rating");
  const tModeration = useTranslations("moderation");
  const sessionId = params.sessionId as string;
  const { leaveSession } = useSessionStore();
  const {
    hasPendingRatings,
    pendingSessionId,
    rateableUsers,
    ratings,
    isSubmitting,
    error: ratingError,
    setRating,
    setReasons,
    setOtherText,
    submitRatings,
    skipAll,
    checkPendingRatings,
  } = useRatingStore();

  const tPartners = useTranslations("partners");
  const { sendRequest } = usePartnerStore();
  const [partnerStatus, setPartnerStatus] = useState<Record<string, string | null>>({});

  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [ratingsCompleted, setRatingsCompleted] = useState(false);
  const [reportPickerOpen, setReportPickerOpen] = useState(false);
  const [reportTarget, setReportTarget] = useState<{
    user_id: string;
    display_name: string;
  } | null>(null);

  // Fetch session summary and pending ratings
  useEffect(() => {
    async function fetchSummary() {
      try {
        const data = await api.get<SessionSummary>(`/sessions/${sessionId}/summary`);
        setSummary(data);
      } catch (err) {
        console.error("Failed to fetch session summary:", err);
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
    checkPendingRatings();
  }, [sessionId, checkPendingRatings]);

  // Clean up session state on unmount
  useEffect(() => {
    return () => {
      leaveSession();
    };
  }, [leaveSession]);

  const allRated =
    rateableUsers.length > 0 && rateableUsers.every((u) => ratings[u.user_id]?.value !== null);

  const hasInvalidRed = rateableUsers.some((u) => {
    const entry = ratings[u.user_id];
    return entry?.value === "red" && entry.reasons.length === 0;
  });

  const canSubmit = allRated && !hasInvalidRed && !isSubmitting;

  const handleSubmitRatings = async () => {
    await submitRatings(sessionId);
    setRatingsCompleted(true);
  };

  const handleSkipAll = async () => {
    await skipAll(sessionId);
    setRatingsCompleted(true);
  };

  const handleSendPartnerRequest = async (userId: string) => {
    try {
      await sendRequest(userId);
      setPartnerStatus((prev) => ({ ...prev, [userId]: "pending" }));
      toast.success(tPartners("requestSent"));
    } catch {
      toast.error(tPartners("createError"));
    }
  };

  const handleReturnHome = () => {
    leaveSession();
    router.push("/dashboard");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{t("loadingSummary")}</p>
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
  const modeLabel = mode === "forced_audio" ? t("forcedAudio") : t("quietMode");

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Success Card */}
        <Card>
          <CardHeader className="text-center pb-2">
            <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-success/20">
              <CheckCircle className="h-10 w-10 text-success" />
            </div>
            <CardTitle className="text-2xl font-bold">{t("title")}</CardTitle>
            <CardDescription>{t("summaryDesc")}</CardDescription>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-4">
              <StatCard
                icon={<Clock className="h-5 w-5 text-primary" />}
                label={t("focusTime")}
                value={t("minutes", { minutes: focusMinutes })}
              />
              <StatCard
                icon={<Sparkles className="h-5 w-5 text-accent" />}
                label={t("essenceEarned")}
                value={essenceEarned ? "+1" : "--"}
              />
              <StatCard
                icon={<Users className="h-5 w-5 text-muted-foreground" />}
                label={t("tablemates")}
                value={String(tablemateCount)}
              />
              <StatCard
                icon={<CheckCircle className="h-5 w-5 text-success" />}
                label={t("phases")}
                value={t("phasesValue", { completed: phasesCompleted, total: totalPhases })}
              />
            </div>

            {/* Session Details */}
            <div className="bg-muted rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{t("sessionId")}</span>
                <code className="text-xs bg-background px-2 py-1 rounded">
                  {sessionId.slice(0, 8)}...
                </code>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{t("duration")}</span>
                <span className="font-medium">{t("durationValue")}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{t("mode")}</span>
                <Badge variant="outline">{modeLabel}</Badge>
              </div>
              {summary?.topic && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{t("topic")}</span>
                  <span className="font-medium">{summary.topic}</span>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Peer Rating Section */}
        {ratingsCompleted ? (
          <Card className="border-success/50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-success/20 flex-shrink-0">
                  <CheckCircle className="h-5 w-5 text-success" />
                </div>
                <div>
                  <h3 className="font-medium">{t("thanksFeedback")}</h3>
                  <p className="text-sm text-muted-foreground">{t("feedbackHelps")}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ) : hasPendingRatings && pendingSessionId === sessionId && rateableUsers.length > 0 ? (
          <Card className="border-accent/50">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/20 flex-shrink-0">
                  <Star className="h-5 w-5 text-accent" />
                </div>
                <div>
                  <CardTitle className="text-base">{t("rateTablemates")}</CardTitle>
                  <CardDescription>{t("rateTablematesQuestion")}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {rateableUsers.map((user) => (
                <RatingCard
                  key={user.user_id}
                  userId={user.user_id}
                  username={user.username}
                  displayName={user.display_name}
                  avatarConfig={user.avatar_config}
                  currentRating={ratings[user.user_id]?.value ?? null}
                  reasons={ratings[user.user_id]?.reasons ?? []}
                  otherReasonText={ratings[user.user_id]?.otherReasonText ?? ""}
                  onRatingChange={(value) => setRating(user.user_id, value)}
                  onReasonsChange={(reasons) => setReasons(user.user_id, reasons)}
                  onOtherTextChange={(text) => setOtherText(user.user_id, text)}
                />
              ))}

              {ratingError && (
                <div className="flex items-center gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  {ratingError}
                </div>
              )}

              {hasInvalidRed && (
                <p className="text-xs text-muted-foreground text-center">{t("redReasonHint")}</p>
              )}

              <div className="flex gap-3 pt-2">
                <Button className="flex-1" onClick={handleSubmitRatings} disabled={!canSubmit}>
                  {isSubmitting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : null}
                  {tRating("submit")}
                </Button>
                <Button variant="ghost" onClick={handleSkipAll} disabled={isSubmitting}>
                  {t("skipAll")}
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {/* Add as Partner */}
        {rateableUsers.length > 0 && (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-3">
                <UserPlus className="h-4 w-4 text-accent" />
                <p className="text-sm font-medium text-foreground">{tPartners("addPartner")}</p>
              </div>
              <div className="space-y-2">
                {rateableUsers.map((user) => (
                  <div
                    key={user.user_id}
                    className="flex items-center justify-between rounded-lg border border-border p-3"
                  >
                    <div className="flex items-center gap-2">
                      <div className="size-7 rounded-full bg-primary/20 flex items-center justify-center text-xs font-medium text-primary">
                        {getInitials(user.display_name || user.username || "U")}
                      </div>
                      <span className="text-sm font-medium text-foreground">
                        {user.display_name || user.username || "User"}
                      </span>
                    </div>
                    <AddPartnerButton
                      userId={user.user_id}
                      partnershipStatus={partnerStatus[user.user_id] ?? null}
                      onSendRequest={handleSendPartnerRequest}
                      compact
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Report a concern */}
        {rateableUsers.length > 0 && (
          <div className="text-center">
            <button
              onClick={() => setReportPickerOpen(true)}
              className="text-sm text-muted-foreground hover:text-destructive transition-colors underline underline-offset-4"
            >
              {tModeration("reportConcern")}
            </button>
          </div>
        )}

        {/* Report Picker Dialog */}
        <Dialog open={reportPickerOpen} onOpenChange={setReportPickerOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Flag className="size-5 text-destructive" />
                {t("reportPickerTitle")}
              </DialogTitle>
              <DialogDescription>{t("reportPickerDesc")}</DialogDescription>
            </DialogHeader>
            <div className="space-y-2">
              {rateableUsers.map((user) => (
                <button
                  key={user.user_id}
                  onClick={() => {
                    setReportTarget({
                      user_id: user.user_id,
                      display_name: user.display_name || user.username || "User",
                    });
                    setReportPickerOpen(false);
                  }}
                  className="w-full flex items-center gap-3 rounded-lg border border-border p-3 hover:bg-muted/50 transition-colors text-left"
                >
                  <div className="size-8 rounded-full bg-primary/20 flex items-center justify-center text-sm font-medium text-primary">
                    {getInitials(user.display_name || user.username || "U")}
                  </div>
                  <span className="text-sm font-medium text-foreground">
                    {user.display_name || user.username || "User"}
                  </span>
                </button>
              ))}
            </div>
          </DialogContent>
        </Dialog>

        {/* Report Modal */}
        {reportTarget && (
          <ReportModal
            isOpen={!!reportTarget}
            onClose={() => setReportTarget(null)}
            reportedUserId={reportTarget.user_id}
            reportedDisplayName={reportTarget.display_name}
            sessionId={sessionId}
          />
        )}

        {/* Return Home Button */}
        <Button size="lg" className="w-full" onClick={handleReturnHome}>
          <Home className="h-4 w-4 mr-2" />
          {t("returnHome")}
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

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}
