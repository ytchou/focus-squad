"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
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
import { PHASE_COLORS, PHASE_LABELS } from "@/lib/session/phase-utils";
import { cn } from "@/lib/utils";

interface SessionHeaderProps {
  sessionId: string;
  phase: SessionPhase;
  onLeave?: () => Promise<void>;
}

export function SessionHeader({ sessionId, phase, onLeave }: SessionHeaderProps) {
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
      <header className="sticky top-0 z-10 bg-surface/80 backdrop-blur border-b border-border px-4 py-3">
        <div className="flex items-center justify-between max-w-2xl mx-auto">
          {/* Phase Badge */}
          <Badge className={cn("text-sm font-medium", PHASE_COLORS[phase])}>
            {PHASE_LABELS[phase]}
          </Badge>

          {/* Leave Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowLeaveDialog(true)}
            className="text-muted-foreground hover:text-destructive"
          >
            <LogOut className="h-4 w-4 mr-2" />
            Leave
          </Button>
        </div>
      </header>

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
