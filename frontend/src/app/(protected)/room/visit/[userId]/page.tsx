"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { AppShell } from "@/components/layout";
import { Loader2 } from "lucide-react";
import { useRoomStore } from "@/stores/room-store";
import { PartnerRoomView } from "@/components/room/partner-room-view";
import { trackRoomVisitViewed } from "@/lib/posthog/events";

export default function VisitPartnerRoomPage() {
  const params = useParams<{ userId: string }>();
  const router = useRouter();
  const t = useTranslations("room");

  const partnerRoom = useRoomStore((s) => s.partnerRoom);
  const isLoading = useRoomStore((s) => s.isPartnerRoomLoading);
  const fetchPartnerRoom = useRoomStore((s) => s.fetchPartnerRoom);
  const clearPartnerRoom = useRoomStore((s) => s.clearPartnerRoom);

  useEffect(() => {
    if (params.userId) {
      trackRoomVisitViewed(params.userId);
      fetchPartnerRoom(params.userId);
    }
    return () => clearPartnerRoom();
  }, [params.userId, fetchPartnerRoom, clearPartnerRoom]);

  if (isLoading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center py-24">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </AppShell>
    );
  }

  if (!partnerRoom) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <p className="text-muted-foreground">{t("partnerRoomError")}</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <PartnerRoomView data={partnerRoom} onBack={() => router.push("/partners")} />
    </AppShell>
  );
}
