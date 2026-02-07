"use client";

import { Mic, MicOff, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ControlBarProps {
  isMuted: boolean;
  isQuietMode: boolean;
  onToggleMute: () => void;
}

export function ControlBar({ isMuted, isQuietMode, onToggleMute }: ControlBarProps) {
  return (
    <div className="flex items-center justify-center gap-6">
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

      {/* Activity Indicator (always on, not toggleable) */}
      <div className="flex flex-col items-center gap-1">
        <div
          className="rounded-full h-14 w-14 p-0 flex items-center justify-center bg-accent text-accent-foreground"
          title="Activity tracking is always enabled"
        >
          <Activity className="h-6 w-6" />
        </div>
        <span className="text-xs text-muted-foreground">Tracking</span>
      </div>

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
