"use client";

import { useState, useRef, useEffect } from "react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Mic, MicOff, Bot, MoreHorizontal, Flag } from "lucide-react";
import { cn } from "@/lib/utils";
import { ReportModal } from "@/components/moderation/report-modal";
import type { PresenceState } from "@/types/activity";

export interface ParticipantSeatProps {
  id: string;
  userId: string | null;
  seatNumber: number;
  username: string | null;
  displayName: string | null;
  isAI: boolean;
  isMuted: boolean;
  presenceState: PresenceState;
  isSpeaking: boolean;
  isCurrentUser: boolean;
  isEmpty?: boolean;
  sessionId: string;
}

export function ParticipantSeat({
  id,
  userId,
  seatNumber: _seatNumber,
  username,
  displayName,
  isAI,
  isMuted,
  presenceState,
  isSpeaking,
  isCurrentUser,
  isEmpty = false,
  sessionId,
}: ParticipantSeatProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    if (!menuOpen) return;

    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [menuOpen]);

  if (isEmpty) {
    return (
      <div className="bg-muted/50 rounded-2xl p-4 flex flex-col items-center gap-2 border border-dashed border-border min-h-[140px] justify-center">
        <div className="size-16 rounded-full bg-muted flex items-center justify-center">
          <span className="text-2xl text-muted-foreground">?</span>
        </div>
        <span className="text-sm text-muted-foreground">Empty Seat</span>
      </div>
    );
  }

  const name = displayName || username || (isAI ? "AI Companion" : "User");
  const initials = getInitials(name);
  const showMenu = !isAI && !isCurrentUser && !!userId;

  return (
    <div
      className={cn(
        "relative bg-card rounded-2xl p-4 flex flex-col items-center gap-2 border border-border transition-all duration-300 min-h-[140px]",
        isCurrentUser && "ring-2 ring-primary ring-offset-2 ring-offset-background",
        isSpeaking && !isMuted && "ring-2 ring-success animate-pulse"
      )}
    >
      {/* Three-dot menu for reportable participants */}
      {showMenu && (
        <div ref={menuRef} className="absolute top-2 right-2 z-10">
          <button
            onClick={() => setMenuOpen((prev) => !prev)}
            className="p-1 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
            aria-label="More options"
          >
            <MoreHorizontal className="size-4" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 w-40 rounded-lg border border-border bg-card shadow-lg py-1 z-20">
              <button
                onClick={() => {
                  setMenuOpen(false);
                  setReportOpen(true);
                }}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-muted transition-colors"
              >
                <Flag className="size-3.5" />
                Report User
              </button>
            </div>
          )}
        </div>
      )}

      {/* Avatar with speaking indicator */}
      <div className="relative">
        <Avatar className="size-16">
          <AvatarFallback
            className={cn(
              "text-lg font-medium",
              isAI ? "bg-accent/20 text-accent" : "bg-primary/20 text-primary"
            )}
          >
            {isAI ? <Bot className="size-6" /> : initials}
          </AvatarFallback>
        </Avatar>

        {/* Speaking pulse ring */}
        {isSpeaking && !isMuted && (
          <div className="absolute inset-0 rounded-full border-2 border-success animate-ping" />
        )}

        {/* Mute indicator */}
        <div
          className={cn(
            "absolute -bottom-1 -right-1 rounded-full p-1",
            isMuted ? "bg-destructive" : "bg-success"
          )}
        >
          {isMuted ? (
            <MicOff className="size-3 text-destructive-foreground" />
          ) : (
            <Mic className="size-3 text-success-foreground" />
          )}
        </div>
      </div>

      {/* Name */}
      <span className="text-sm font-medium truncate max-w-full text-center">
        {isCurrentUser ? `${name} (You)` : name}
      </span>

      {/* Status badges */}
      <div className="flex gap-1 flex-wrap justify-center">
        {isAI && (
          <Badge variant="outline" className="text-xs">
            AI
          </Badge>
        )}
        {!isAI && (
          <Badge
            variant={
              presenceState === "active" || presenceState === "grace" ? "default" : "secondary"
            }
            className={cn(
              "text-xs",
              (presenceState === "active" || presenceState === "grace") &&
                "bg-success text-success-foreground",
              presenceState === "away" && "bg-warning text-warning-foreground"
            )}
          >
            {presenceState === "active" || presenceState === "grace"
              ? "Focused"
              : presenceState === "away"
                ? "Away"
                : "Gone"}
          </Badge>
        )}
      </div>

      {/* Report Modal */}
      {showMenu && (
        <ReportModal
          isOpen={reportOpen}
          onClose={() => setReportOpen(false)}
          reportedUserId={userId!}
          reportedDisplayName={name}
          sessionId={sessionId}
        />
      )}
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
