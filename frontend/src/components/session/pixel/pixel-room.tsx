"use client";

import { PIXEL_ROOMS, DEFAULT_ROOM } from "@/config/pixel-rooms";
import { RoomAmbientAnimation } from "./room-ambient-animation";

interface PixelRoomProps {
  roomType: string;
  children?: React.ReactNode;
}

export function PixelRoom({ roomType, children }: PixelRoomProps) {
  const room = PIXEL_ROOMS[roomType] ?? PIXEL_ROOMS[DEFAULT_ROOM];

  return (
    <div className="relative w-full h-full">
      {/* Room background */}
      <div
        className="absolute inset-0 z-0"
        style={{
          backgroundImage: `url(${room.backgroundImage})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundRepeat: "no-repeat",
          imageRendering: "pixelated",
        }}
      />
      {/* Slight warm overlay to unify art with design tokens */}
      <div className="absolute inset-0 z-[1] bg-background/10 pointer-events-none" />
      {/* Ambient animations (z-[5], between background and characters) */}
      <RoomAmbientAnimation roomType={roomType} />
      {/* Content layers (characters at z-10, UI at z-20) */}
      {children}
    </div>
  );
}
