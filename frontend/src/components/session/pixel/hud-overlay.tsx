"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { SessionPhase } from "@/stores/session-store";
import { PHASE_COLORS, PHASE_LABELS, formatTime } from "@/lib/session/phase-utils";
import { cn } from "@/lib/utils";

interface HudOverlayProps {
  sessionId: string;
  phase: SessionPhase;
  timeRemaining: number;
  totalTimeRemaining: number;
  onLeave?: () => Promise<void>;
}

export function HudOverlay({
  sessionId: _sessionId,
  phase,
  timeRemaining,
  totalTimeRemaining: _totalTimeRemaining,
  onLeave,
}: HudOverlayProps) {
  const router = useRouter();
  const [showLeaveDialog, setShowLeaveDialog] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  const handleLeave = async () => {
    setIsLeaving(true);
    try {
      if (onLeave) {
        await onLeave();
      }
      router.push("/dashboard");
    } catch (error) {
      console.error("Failed to leave session:", error);
      setIsLeaving(false);
    }
  };

  return (
    <>
      <div className="fixed top-0 left-0 right-0 z-20 bg-foreground/90 shadow-pixel px-4 py-2 border-b-2 border-border/80">
        <div className="flex items-center justify-between max-w-screen-xl mx-auto">
          {/* Phase Badge */}
          <Badge
            className={cn("text-sm font-pixel text-[0.55rem] rounded-pixel", PHASE_COLORS[phase])}
          >
            {PHASE_LABELS[phase]}
          </Badge>

          {/* Timer */}
          <div className="flex items-center gap-2 text-primary-foreground">
            <Clock className="h-4 w-4" />
            <span className="font-pixel text-[0.7rem] tracking-wider">
              {formatTime(timeRemaining)}
            </span>
          </div>

          {/* Leave Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowLeaveDialog(true)}
            className="text-primary-foreground/70 hover:text-primary-foreground hover:bg-primary-foreground/10 rounded-pixel"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Leave Confirmation Dialog */}
      <Dialog open={showLeaveDialog} onOpenChange={setShowLeaveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Leave Session?</DialogTitle>
            <DialogDescription>
              If you leave now, you won&apos;t be able to rejoin this session and your credit will
              not be refunded. Your tablemates will continue without you.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setShowLeaveDialog(false)}
              disabled={isLeaving}
            >
              Stay
            </Button>
            <Button variant="destructive" onClick={handleLeave} disabled={isLeaving}>
              {isLeaving ? "Leaving..." : "Leave Session"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
