"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { AMBIENT_TRACKS, AMBIENT_STORAGE_KEY } from "@/config/ambient-tracks";

interface TrackState {
  enabled: boolean;
  volume: number;
}

interface UseAmbientMixerReturn {
  tracks: Record<string, TrackState>;
  isReady: boolean;
  toggleTrack: (trackId: string) => void;
  setVolume: (trackId: string, volume: number) => void;
}

interface AudioNodes {
  source: AudioBufferSourceNode;
  gain: GainNode;
}

function buildDefaultTracks(): Record<string, TrackState> {
  const tracks: Record<string, TrackState> = {};
  for (const t of AMBIENT_TRACKS) {
    tracks[t.id] = { enabled: false, volume: t.defaultVolume };
  }
  return tracks;
}

function loadPersistedTracks(): Record<string, TrackState> {
  if (typeof window === "undefined") return buildDefaultTracks();

  try {
    const raw = localStorage.getItem(AMBIENT_STORAGE_KEY);
    if (!raw) return buildDefaultTracks();
    const parsed = JSON.parse(raw) as Record<string, TrackState>;

    const defaults = buildDefaultTracks();
    for (const id of Object.keys(defaults)) {
      if (parsed[id]) {
        defaults[id] = {
          enabled: parsed[id].enabled,
          volume: Math.max(0, Math.min(1, parsed[id].volume)),
        };
      }
    }
    return defaults;
  } catch {
    return buildDefaultTracks();
  }
}

function persistTracks(tracks: Record<string, TrackState>): void {
  try {
    localStorage.setItem(AMBIENT_STORAGE_KEY, JSON.stringify(tracks));
  } catch {
    // localStorage may be full or unavailable
  }
}

export function useAmbientMixer(): UseAmbientMixerReturn {
  const [tracks, setTracks] = useState<Record<string, TrackState>>(loadPersistedTracks);
  const [isReady, setIsReady] = useState(false);

  const audioContextRef = useRef<AudioContext | null>(null);
  const buffersRef = useRef<Record<string, AudioBuffer>>({});
  const nodesRef = useRef<Record<string, AudioNodes>>({});
  const loadingRef = useRef<Record<string, boolean>>({});

  const ensureAudioContext = useCallback(async (): Promise<AudioContext> => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
    }

    const ctx = audioContextRef.current;
    if (ctx.state === "suspended") {
      await ctx.resume();
    }

    if (!isReady) {
      setIsReady(true);
    }

    return ctx;
  }, [isReady]);

  const fetchAndDecode = useCallback(
    async (trackId: string, audioSrc: string): Promise<AudioBuffer> => {
      if (buffersRef.current[trackId]) {
        return buffersRef.current[trackId];
      }

      const ctx = await ensureAudioContext();
      const response = await fetch(audioSrc);
      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
      buffersRef.current[trackId] = audioBuffer;
      return audioBuffer;
    },
    [ensureAudioContext]
  );

  const startPlayback = useCallback(
    async (trackId: string, volume: number) => {
      const track = AMBIENT_TRACKS.find((t) => t.id === trackId);
      if (!track) return;

      if (loadingRef.current[trackId]) return;
      loadingRef.current[trackId] = true;

      try {
        const ctx = await ensureAudioContext();
        const buffer = await fetchAndDecode(trackId, track.audioSrc);

        if (nodesRef.current[trackId]) {
          try {
            nodesRef.current[trackId].source.stop();
            nodesRef.current[trackId].source.disconnect();
            nodesRef.current[trackId].gain.disconnect();
          } catch {
            // source may already be stopped
          }
        }

        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.loop = true;

        const gain = ctx.createGain();
        gain.gain.setValueAtTime(volume, ctx.currentTime);

        source.connect(gain);
        gain.connect(ctx.destination);
        source.start();

        nodesRef.current[trackId] = { source, gain };
      } finally {
        loadingRef.current[trackId] = false;
      }
    },
    [ensureAudioContext, fetchAndDecode]
  );

  const stopPlayback = useCallback((trackId: string) => {
    const nodes = nodesRef.current[trackId];
    if (!nodes) return;

    try {
      nodes.source.stop();
      nodes.source.disconnect();
      nodes.gain.disconnect();
    } catch {
      // source may already be stopped
    }

    delete nodesRef.current[trackId];
  }, []);

  const toggleTrack = useCallback(
    (trackId: string) => {
      setTracks((prev) => {
        const current = prev[trackId];
        if (!current) return prev;

        const next = {
          ...prev,
          [trackId]: { ...current, enabled: !current.enabled },
        };

        if (!current.enabled) {
          startPlayback(trackId, current.volume);
        } else {
          stopPlayback(trackId);
        }

        persistTracks(next);
        return next;
      });
    },
    [startPlayback, stopPlayback]
  );

  const setVolume = useCallback(
    (trackId: string, volume: number) => {
      const clamped = Math.max(0, Math.min(1, volume));

      setTracks((prev) => {
        const current = prev[trackId];
        if (!current) return prev;

        const next = {
          ...prev,
          [trackId]: { ...current, volume: clamped },
        };

        persistTracks(next);
        return next;
      });

      const nodes = nodesRef.current[trackId];
      if (nodes && audioContextRef.current) {
        const ctx = audioContextRef.current;
        nodes.gain.gain.linearRampToValueAtTime(clamped, ctx.currentTime + 0.05);
      } else if (!nodesRef.current[trackId]) {
        ensureAudioContext();
      }
    },
    [ensureAudioContext]
  );

  useEffect(() => {
    return () => {
      for (const trackId of Object.keys(nodesRef.current)) {
        try {
          nodesRef.current[trackId].source.stop();
          nodesRef.current[trackId].source.disconnect();
          nodesRef.current[trackId].gain.disconnect();
        } catch {
          // source may already be stopped
        }
      }
      nodesRef.current = {};

      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
    };
  }, []);

  return { tracks, isReady, toggleTrack, setVolume };
}
