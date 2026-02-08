"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Bot, Mic, MicOff } from "lucide-react";
import { cn } from "@/lib/utils";

interface CompactParticipant {
  id: string;
  livekitIdentity: string | null;
  displayName: string | null;
  username: string | null;
  isAI: boolean;
  isMuted: boolean;
  isCurrentUser: boolean;
}

interface CompactTableViewProps {
  participants: CompactParticipant[];
  speakingParticipantIds: Set<string>;
}

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  return words.length >= 2
    ? (words[0][0] + words[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

export function CompactTableView({ participants, speakingParticipantIds }: CompactTableViewProps) {
  return (
    <div className="flex items-center justify-center gap-3 py-2">
      {[1, 2, 3, 4].map((seatNum) => {
        const p = participants[seatNum - 1];
        if (!p) {
          return (
            <div
              key={`empty-${seatNum}`}
              className="size-10 rounded-full bg-muted/50 border border-dashed border-border flex items-center justify-center"
            >
              <span className="text-xs text-muted-foreground">?</span>
            </div>
          );
        }

        const name = p.displayName || p.username || (p.isAI ? "AI" : "User");
        const isSpeaking = p.livekitIdentity
          ? speakingParticipantIds.has(p.livekitIdentity)
          : false;

        return (
          <div key={p.id} className="flex flex-col items-center gap-0.5">
            <div className="relative">
              <Avatar
                className={cn(
                  "size-10",
                  p.isCurrentUser && "ring-2 ring-primary ring-offset-1 ring-offset-background",
                  isSpeaking && !p.isMuted && "ring-2 ring-success"
                )}
              >
                <AvatarFallback
                  className={cn(
                    "text-xs",
                    p.isAI ? "bg-accent/20 text-accent" : "bg-primary/20 text-primary"
                  )}
                >
                  {p.isAI ? <Bot className="size-3.5" /> : getInitials(name)}
                </AvatarFallback>
              </Avatar>
              <div
                className={cn(
                  "absolute -bottom-0.5 -right-0.5 rounded-full p-0.5",
                  p.isMuted ? "bg-destructive" : "bg-success"
                )}
              >
                {p.isMuted ? (
                  <MicOff className="size-2 text-destructive-foreground" />
                ) : (
                  <Mic className="size-2 text-success-foreground" />
                )}
              </div>
            </div>
            <span className="text-[10px] text-muted-foreground truncate max-w-[48px]">
              {p.isCurrentUser ? "You" : name.split(" ")[0]}
            </span>
          </div>
        );
      })}
    </div>
  );
}
