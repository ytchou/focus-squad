"use client";

import { useTranslations } from "next-intl";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RoomGrid } from "./room-grid";
import type { PartnerRoomResponse } from "@/stores/room-store";

interface PartnerRoomViewProps {
  data: PartnerRoomResponse;
  onBack: () => void;
}

export function PartnerRoomView({ data, onBack }: PartnerRoomViewProps) {
  const t = useTranslations("room");

  const overrideData = {
    room: {
      room_type: data.room.room_type,
      layout: data.room.layout,
      active_companion: data.room.active_companion,
    },
    inventory: data.inventory,
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
          {t("partnerRoomBack")}
        </Button>
        <div className="flex-1">
          <h1 className="text-xl font-semibold text-foreground">
            {t("partnerRoom", { name: data.owner_name })}
          </h1>
          <p className="text-sm text-muted-foreground">@{data.owner_username}</p>
        </div>
      </div>

      {/* Room grid (read-only) */}
      <div className="rounded-xl border border-border overflow-hidden bg-card">
        <RoomGrid overrideData={overrideData} readOnly />
      </div>

      {/* Companion count */}
      {data.companions.length > 0 && (
        <p className="text-sm text-muted-foreground text-center">
          {data.companions.filter((c) => c.adopted_at).length} companion
          {data.companions.filter((c) => c.adopted_at).length !== 1 ? "s" : ""} adopted
        </p>
      )}
    </div>
  );
}
