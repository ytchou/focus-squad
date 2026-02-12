"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { useRoomStore } from "@/stores/room-store";
import { toast } from "sonner";
import { Gift } from "lucide-react";

export function GiftNotificationToast() {
  const t = useTranslations("room");
  const fetchUnseenGifts = useRoomStore((s) => s.fetchUnseenGifts);
  const markGiftsSeen = useRoomStore((s) => s.markGiftsSeen);
  const hasFetched = useRef(false);

  useEffect(() => {
    if (hasFetched.current) return;
    hasFetched.current = true;

    fetchUnseenGifts().then((gifts) => {
      if (gifts.length === 0) return;

      for (const gift of gifts) {
        const itemName = gift.item_name_zh || gift.item_name;
        toast(t("giftReceived", { sender: gift.gifted_by_name, item: itemName }), {
          icon: <Gift className="h-4 w-4 text-accent" />,
          description: gift.gift_message || undefined,
          duration: 6000,
        });
      }

      const ids = gifts.map((g) => g.inventory_item_id);
      markGiftsSeen(ids);
    });
  }, [fetchUnseenGifts, markGiftsSeen, t]);

  return null;
}
