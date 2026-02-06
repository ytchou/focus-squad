"use client";

import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { CheckCircle, Star, Clock } from "lucide-react";
import type { SessionPhase } from "@/stores/session-store";

interface SessionEndModalProps {
  open: boolean;
  onClose: () => void;
  sessionId: string;
  phase: SessionPhase;
}

export function SessionEndModal({ open, onClose, sessionId, phase }: SessionEndModalProps) {
  const router = useRouter();

  const isCompleted = phase === "completed";
  const isSocialPhase = phase === "social";

  const handleViewSummary = () => {
    onClose();
    router.push(`/session/${sessionId}/end`);
  };

  const handleRateTablemates = () => {
    // Rating UI is Phase 3 - for now just show a message or link to summary
    onClose();
    router.push(`/session/${sessionId}/end`);
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-success/20">
            {isCompleted ? (
              <CheckCircle className="h-8 w-8 text-success" />
            ) : (
              <Clock className="h-8 w-8 text-accent" />
            )}
          </div>
          <DialogTitle className="text-center text-xl">
            {isCompleted ? "Session Complete!" : "Social Time"}
          </DialogTitle>
          <DialogDescription className="text-center">
            {isCompleted
              ? "Great work! You've completed your focus session."
              : "The work blocks are done. Take a moment to chat with your tablemates."}
          </DialogDescription>
        </DialogHeader>

        {/* Stats Summary */}
        <div className="bg-muted rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Session Duration</span>
            <span className="font-medium">55 minutes</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Focus Time</span>
            <span className="font-medium">47 minutes</span>
          </div>
          {isCompleted && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Essence Earned</span>
              <span className="font-medium text-accent">+1 Furniture Essence</span>
            </div>
          )}
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-col">
          {isSocialPhase && (
            <Button variant="default" className="w-full" onClick={handleRateTablemates}>
              <Star className="h-4 w-4 mr-2" />
              Rate Tablemates
            </Button>
          )}
          <Button
            variant={isSocialPhase ? "outline" : "default"}
            className="w-full"
            onClick={handleViewSummary}
          >
            {isCompleted ? "View Summary" : "Continue Session"}
          </Button>
          {isSocialPhase && (
            <p className="text-xs text-muted-foreground text-center">
              Session ends in 5 minutes. Rating helps build trust in the community.
            </p>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
