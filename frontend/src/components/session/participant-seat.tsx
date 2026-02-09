"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Mic, MicOff, Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PresenceState } from "@/types/activity";

export interface ParticipantSeatProps {
  id: string;
  seatNumber: number;
  username: string | null;
  displayName: string | null;
  isAI: boolean;
  isMuted: boolean;
  presenceState: PresenceState;
  isSpeaking: boolean;
  isCurrentUser: boolean;
  isEmpty?: boolean;
}

export function ParticipantSeat({
  seatNumber: _seatNumber,
  username,
  displayName,
  isAI,
  isMuted,
  presenceState,
  isSpeaking,
  isCurrentUser,
  isEmpty = false,
}: ParticipantSeatProps) {
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

  return (
    <div
      className={cn(
        "bg-card rounded-2xl p-4 flex flex-col items-center gap-2 border border-border transition-all duration-300 min-h-[140px]",
        isCurrentUser && "ring-2 ring-primary ring-offset-2 ring-offset-background",
        isSpeaking && !isMuted && "ring-2 ring-success animate-pulse"
      )}
    >
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
