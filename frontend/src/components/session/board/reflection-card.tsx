"use client";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Target, Coffee, MessageCircle } from "lucide-react";
import type { BoardMessage, ReflectionPhase } from "@/stores/board-store";

interface ReflectionCardProps {
  message: BoardMessage;
  isOwnMessage: boolean;
}

const PHASE_CONFIG: Record<
  ReflectionPhase,
  { label: string; icon: typeof Target; className: string }
> = {
  setup: {
    label: "Session Goal",
    icon: Target,
    className: "bg-primary/10 border-primary/20",
  },
  break: {
    label: "Check-in",
    icon: Coffee,
    className: "bg-success/10 border-success/20",
  },
  social: {
    label: "Afterthoughts",
    icon: MessageCircle,
    className: "bg-accent/10 border-accent/20",
  },
};

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  return words.length >= 2
    ? (words[0][0] + words[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ReflectionCard({ message, isOwnMessage }: ReflectionCardProps) {
  const phase = message.phase || "setup";
  const config = PHASE_CONFIG[phase];
  const Icon = config.icon;

  return (
    <div className={`rounded-xl border p-3 ${config.className}`}>
      <div className="flex items-center gap-2 mb-2">
        <Avatar className="size-6 shrink-0">
          <AvatarFallback className="text-[10px] bg-primary/20 text-primary">
            {getInitials(message.displayName)}
          </AvatarFallback>
        </Avatar>
        <span className="text-xs font-medium text-foreground">
          {isOwnMessage ? "You" : message.displayName}
        </span>
        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 gap-0.5">
          <Icon className="size-2.5" />
          {config.label}
        </Badge>
        <span className="text-[10px] text-muted-foreground ml-auto">
          {formatTime(message.timestamp)}
        </span>
      </div>
      <p className="text-sm text-foreground leading-relaxed pl-8">{message.content}</p>
    </div>
  );
}
