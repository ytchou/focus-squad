"use client";

import { type ReactNode, useCallback, useEffect, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
  useLocalParticipant,
  useParticipants,
} from "@livekit/components-react";
import { RoomEvent, ConnectionState, DataPacket_Kind } from "livekit-client";
import { ConnectionStatus } from "./connection-status";

interface LiveKitRoomProviderProps {
  token: string;
  serverUrl: string;
  isQuietMode: boolean;
  onConnectionStateChange?: (
    state: "connected" | "connecting" | "reconnecting" | "disconnected"
  ) => void;
  children: ReactNode;
}

/**
 * Wrapper around LiveKitRoom that handles:
 * - Connection state management
 * - Audio-only configuration
 * - Quiet mode (no audio publish)
 * - Connection status display
 */
export function LiveKitRoomProvider({
  token,
  serverUrl,
  isQuietMode,
  onConnectionStateChange,
  children,
}: LiveKitRoomProviderProps) {
  const [connectionState, setConnectionState] = useState<
    "connected" | "connecting" | "reconnecting" | "disconnected"
  >("connecting");
  const [disconnectedAt, setDisconnectedAt] = useState<Date | null>(null);

  const handleConnectionStateChange = useCallback(
    (state: ConnectionState) => {
      let mappedState: "connected" | "connecting" | "reconnecting" | "disconnected";

      switch (state) {
        case ConnectionState.Connected:
          mappedState = "connected";
          setDisconnectedAt(null);
          break;
        case ConnectionState.Connecting:
          mappedState = "connecting";
          break;
        case ConnectionState.Reconnecting:
          mappedState = "reconnecting";
          if (!disconnectedAt) {
            setDisconnectedAt(new Date());
          }
          break;
        case ConnectionState.Disconnected:
          mappedState = "disconnected";
          if (!disconnectedAt) {
            setDisconnectedAt(new Date());
          }
          break;
        default:
          mappedState = "connecting";
      }

      setConnectionState(mappedState);
      onConnectionStateChange?.(mappedState);
    },
    [disconnectedAt, onConnectionStateChange]
  );

  return (
    <LiveKitRoom
      token={token}
      serverUrl={serverUrl}
      connect={true}
      audio={!isQuietMode} // Forced Audio: mic on, Quiet Mode: mic off
      video={false} // Audio-only platform
      onConnected={() => handleConnectionStateChange(ConnectionState.Connected)}
      onDisconnected={() => handleConnectionStateChange(ConnectionState.Disconnected)}
      onError={(error) => {
        console.error("LiveKit error:", error);
        handleConnectionStateChange(ConnectionState.Disconnected);
      }}
    >
      <ConnectionStatus state={connectionState} disconnectedAt={disconnectedAt} />
      {children}
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

/**
 * Hook to get active speakers from the room.
 * Returns a Set of participant identities who are currently speaking.
 */
export function useActiveSpeakers(): Set<string> {
  const room = useRoomContext();
  const [activeSpeakers, setActiveSpeakers] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!room) return;

    const handleActiveSpeakersChanged = () => {
      const speakers = room.activeSpeakers.map((p) => p.identity);
      setActiveSpeakers(new Set(speakers));
    };

    room.on(RoomEvent.ActiveSpeakersChanged, handleActiveSpeakersChanged);

    return () => {
      room.off(RoomEvent.ActiveSpeakersChanged, handleActiveSpeakersChanged);
    };
  }, [room]);

  return activeSpeakers;
}

/**
 * Hook to control local participant's microphone.
 */
export function useLocalMicrophone() {
  const { localParticipant } = useLocalParticipant();

  // Derive muted state directly from participant (no useState needed)
  const isMuted = localParticipant ? !localParticipant.isMicrophoneEnabled : true;

  const toggleMute = useCallback(async () => {
    if (!localParticipant) return;

    try {
      await localParticipant.setMicrophoneEnabled(isMuted);
    } catch (error) {
      console.error("Failed to toggle microphone:", error);
    }
  }, [localParticipant, isMuted]);

  return { isMuted, toggleMute };
}

/**
 * Hook to get all remote participants.
 */
export function useRemoteParticipants() {
  const participants = useParticipants();
  // Filter out local participant
  return participants.filter((p) => !p.isLocal);
}

/**
 * Hook for sending and receiving data channel messages.
 *
 * Used by the Session Board to broadcast chat/reflection messages
 * to all participants in real-time.
 */
export function useDataChannel(onMessage: (data: unknown) => void) {
  const room = useRoomContext();

  useEffect(() => {
    if (!room) return;

    const handleDataReceived = (
      payload: Uint8Array,
      _participant?: unknown,
      _kind?: DataPacket_Kind
    ) => {
      try {
        const decoded = new TextDecoder().decode(payload);
        const parsed = JSON.parse(decoded);
        onMessage(parsed);
      } catch (err) {
        console.error("Failed to parse data channel message:", err);
      }
    };

    room.on(RoomEvent.DataReceived, handleDataReceived);

    return () => {
      room.off(RoomEvent.DataReceived, handleDataReceived);
    };
  }, [room, onMessage]);

  const sendMessage = useCallback(
    (data: unknown) => {
      if (!room?.localParticipant) return;

      const encoded = new TextEncoder().encode(JSON.stringify(data));
      room.localParticipant.publishData(encoded, { reliable: true });
    },
    [room]
  );

  return { sendMessage };
}
