"use client";

import { Music, Coffee, CloudRain } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAmbientMixer } from "@/hooks/use-ambient-mixer";
import { AMBIENT_TRACKS } from "@/config/ambient-tracks";

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  Music,
  Coffee,
  CloudRain,
};

interface AmbientMixerControlsProps {
  isPixelMode?: boolean;
}

export function AmbientMixerControls({ isPixelMode }: AmbientMixerControlsProps = {}) {
  const { tracks, toggleTrack, setVolume } = useAmbientMixer();

  return (
    <div className="flex items-center gap-2">
      {AMBIENT_TRACKS.map((track) => {
        const Icon = ICON_MAP[track.icon];
        const state = tracks[track.id];
        if (!state || !Icon) return null;

        return (
          <div key={track.id} className="flex flex-col items-center gap-1">
            <button
              onClick={() => toggleTrack(track.id)}
              className={cn(
                "h-10 w-10 flex items-center justify-center transition-colors",
                isPixelMode ? "rounded-pixel shadow-pixel" : "rounded-xl",
                state.enabled
                  ? "bg-accent text-accent-foreground"
                  : "bg-muted/60 text-muted-foreground hover:bg-muted"
              )}
              title={`${state.enabled ? "Disable" : "Enable"} ${track.name}`}
            >
              <Icon className="h-4 w-4" />
            </button>
            <span
              className={cn(
                "text-[10px] text-muted-foreground",
                isPixelMode && "font-pixel text-[0.4rem]"
              )}
            >
              {track.name}
            </span>
            {state.enabled && (
              <input
                type="range"
                min="0"
                max="100"
                value={Math.round(state.volume * 100)}
                onChange={(e) => setVolume(track.id, parseInt(e.target.value) / 100)}
                className="w-10 h-1 accent-accent cursor-pointer"
                title={`${track.name} volume: ${Math.round(state.volume * 100)}%`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
