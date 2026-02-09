"use client";

import { Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { PresenceState } from "@/types/activity";
import { AmbientMixerControls } from "./ambient-mixer-controls";

interface ControlBarProps {
  isMuted: boolean;
  isQuietMode: boolean;
  onToggleMute: () => void;
  presenceState?: PresenceState;
}

const PRESENCE_CONFIG: Record<PresenceState, { color: string; label: string }> = {
  active: { color: "bg-success", label: "Active" },
  grace: { color: "bg-success", label: "Active" },
  away: { color: "bg-warning", label: "Away" },
  ghosting: { color: "bg-destructive", label: "Away" },
};

export function ControlBar({ isMuted, isQuietMode, onToggleMute, presenceState }: ControlBarProps) {
  const presence = presenceState ? PRESENCE_CONFIG[presenceState] : null;

  return (
    <div className="flex items-center justify-center gap-6 py-2">
      {/* Mute/Unmute Button */}
      <div className="flex flex-col items-center gap-1">
        <Button
          variant={isMuted ? "destructive" : "default"}
          size="lg"
          onClick={onToggleMute}
          disabled={isQuietMode}
          className={cn("rounded-full h-14 w-14 p-0", !isMuted && "bg-success hover:bg-success/90")}
          title={isQuietMode ? "Audio disabled in Quiet Mode" : isMuted ? "Unmute" : "Mute"}
        >
          {isMuted ? <MicOff className="h-6 w-6" /> : <Mic className="h-6 w-6" />}
        </Button>
        <span className="text-xs text-muted-foreground">
          {isQuietMode ? "Quiet Mode" : isMuted ? "Unmute" : "Mute"}
        </span>
      </div>

      {/* Presence Indicator */}
      {presence && (
        <div className="flex flex-col items-center gap-1">
          <div className="rounded-full h-10 w-10 flex items-center justify-center bg-muted/60">
            <div className={cn("h-3 w-3 rounded-full", presence.color)} />
          </div>
          <span className="text-[10px] text-muted-foreground">{presence.label}</span>
        </div>
      )}

      {/* Divider */}
      <div className="h-8 w-px bg-border" />

      {/* Ambient Sound Mixer */}
      <AmbientMixerControls />

      {/* Quiet Mode Indicator */}
      {isQuietMode && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2">
          <span className="text-xs text-muted-foreground bg-muted px-3 py-1 rounded-full">
            Quiet Mode - Audio Disabled
          </span>
        </div>
      )}
    </div>
  );
}
