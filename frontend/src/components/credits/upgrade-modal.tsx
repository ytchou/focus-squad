"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Clock, Crown, Gift, Bell, Copy, Check, Sparkles } from "lucide-react";
import { useCountdown } from "@/hooks/use-countdown";
import { useCreditsStore } from "@/stores";
import { api } from "@/lib/api/client";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const TIER_FEATURES = [
  { feature: "Credits / week", free: "2", pro: "8", elite: "12" },
  { feature: "Gift credits", free: "--", pro: "4 / week", elite: "4 / week" },
  { feature: "Priority matching", free: "--", pro: "Yes", elite: "Yes" },
] as const;

const NOTIFY_STORAGE_KEY = "focus-squad-upgrade-notified";

interface ReferralInfo {
  referral_code: string;
  referrals_completed: number;
  shareable_link: string;
}

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UpgradeModal({ isOpen, onClose }: UpgradeModalProps) {
  const refreshDate = useCreditsStore((s) => s.refreshDate);
  const tier = useCreditsStore((s) => s.tier);
  const { countdown } = useCountdown(refreshDate);

  const [referral, setReferral] = useState<ReferralInfo | null>(null);
  const [referralLoading, setReferralLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [notified, setNotified] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(NOTIFY_STORAGE_KEY) === "true";
  });
  const [notifyLoading, setNotifyLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setReferralLoading(true);
    api
      .get<ReferralInfo>("/api/v1/credits/referral")
      .then(setReferral)
      .catch(() => {})
      .finally(() => setReferralLoading(false));
  }, [isOpen]);

  const handleCopyLink = async () => {
    if (!referral?.shareable_link) return;
    await navigator.clipboard.writeText(referral.shareable_link);
    setCopied(true);
    toast.success("Referral link copied!");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleNotifyMe = async () => {
    setNotifyLoading(true);
    try {
      await api.post("/api/v1/credits/notify-interest", {});
      setNotified(true);
      localStorage.setItem(NOTIFY_STORAGE_KEY, "true");
      toast.success("We'll notify you when pricing is available!");
    } catch {
      toast.error("Something went wrong. Please try again.");
    } finally {
      setNotifyLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-accent" />
            Get More Credits
          </DialogTitle>
          <DialogDescription>Here are your options to get back to focusing.</DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-2">
          {/* Section A: Countdown */}
          <div className="flex items-center gap-3 rounded-xl bg-warning/5 border border-warning/30 p-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-warning/20">
              <Clock className="h-5 w-5 text-warning" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Your credits refresh in</p>
              <p className="text-lg font-semibold text-foreground">{countdown}</p>
              <p className="text-xs text-muted-foreground capitalize">
                {tier} plan: {tier === "free" ? "2" : tier === "pro" ? "8" : "12"} credits / week
              </p>
            </div>
          </div>

          {/* Section B: Tier Comparison */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Crown className="h-4 w-4 text-accent" />
              <h3 className="text-sm font-medium text-foreground">Upgrade Your Plan</h3>
            </div>
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-muted/50">
                    <th className="text-left px-3 py-2 text-muted-foreground font-medium" />
                    <th
                      className={cn(
                        "px-3 py-2 text-center font-medium",
                        tier === "free" ? "text-foreground bg-accent/10" : "text-muted-foreground"
                      )}
                    >
                      Free
                    </th>
                    <th
                      className={cn(
                        "px-3 py-2 text-center font-medium",
                        tier === "pro" ? "text-foreground bg-accent/10" : "text-muted-foreground"
                      )}
                    >
                      Pro
                    </th>
                    <th
                      className={cn(
                        "px-3 py-2 text-center font-medium",
                        tier === "elite" ? "text-foreground bg-accent/10" : "text-muted-foreground"
                      )}
                    >
                      Elite
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {TIER_FEATURES.map((row) => (
                    <tr key={row.feature} className="border-t border-border">
                      <td className="px-3 py-2 text-muted-foreground">{row.feature}</td>
                      <td className={cn("px-3 py-2 text-center", tier === "free" && "bg-accent/5")}>
                        {row.free}
                      </td>
                      <td className={cn("px-3 py-2 text-center", tier === "pro" && "bg-accent/5")}>
                        {row.pro}
                      </td>
                      <td
                        className={cn("px-3 py-2 text-center", tier === "elite" && "bg-accent/5")}
                      >
                        {row.elite}
                      </td>
                    </tr>
                  ))}
                  <tr className="border-t border-border">
                    <td className="px-3 py-2 text-muted-foreground">Price</td>
                    <td className="px-3 py-2 text-center text-muted-foreground">Current</td>
                    <td className="px-3 py-2 text-center">
                      <span className="inline-block rounded-full bg-accent/10 text-accent text-xs px-2 py-0.5">
                        Coming Soon
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className="inline-block rounded-full bg-accent/10 text-accent text-xs px-2 py-0.5">
                        Coming Soon
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={handleNotifyMe}
              disabled={notified || notifyLoading}
            >
              <Bell className="h-4 w-4" />
              {notified ? "We'll notify you!" : "Notify me when available"}
            </Button>
          </div>

          {/* Section C: Referral */}
          <div className="rounded-xl bg-success/5 border border-success/30 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Gift className="h-4 w-4 text-success" />
              <h3 className="text-sm font-medium text-foreground">Earn a free credit</h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Refer a friend — you both earn 1 credit when they complete their first session.
            </p>
            {referralLoading ? (
              <div className="h-9 rounded-lg bg-muted animate-pulse" />
            ) : referral ? (
              <Button variant="outline" size="sm" className="w-full" onClick={handleCopyLink}>
                {copied ? (
                  <>
                    <Check className="h-4 w-4 text-success" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    Copy referral link
                  </>
                )}
              </Button>
            ) : null}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
