"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, ShoppingBag, Package, Loader2, Gift } from "lucide-react";
import { useUIStore, useGamificationStore } from "@/stores";
import { useShopStore } from "@/stores/shop-store";
import { useRoomStore } from "@/stores/room-store";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { EssenceBadge } from "./essence-badge";
import { PartnerGiftSelector } from "./partner-gift-selector";

const CATEGORIES = [
  { key: "all", icon: "🏠" },
  { key: "furniture", icon: "🪑" },
  { key: "decor", icon: "🖼️" },
  { key: "plant", icon: "🌿" },
  { key: "pet_accessory", icon: "🐾" },
  { key: "seasonal", icon: "🎄" },
];

const TIER_COLORS: Record<string, string> = {
  basic: "bg-muted text-muted-foreground",
  standard: "bg-accent/20 text-accent",
  premium: "bg-warning/20 text-warning",
};

export function ItemShop() {
  const t = useTranslations("shop");
  const activeModal = useUIStore((s) => s.activeModal);
  const closeModal = useUIStore((s) => s.closeModal);
  const isOpen = activeModal === "shop";

  const catalog = useShopStore((s) => s.catalog);
  const essenceBalance = useShopStore((s) => s.essenceBalance);
  const isLoading = useShopStore((s) => s.isLoading);
  const isPurchasing = useShopStore((s) => s.isPurchasing);
  const isGifting = useShopStore((s) => s.isGifting);
  const selectedRecipientId = useShopStore((s) => s.selectedRecipientId);
  const fetchShop = useShopStore((s) => s.fetchShop);
  const fetchBalance = useShopStore((s) => s.fetchBalance);
  const buyItem = useShopStore((s) => s.buyItem);
  const giftItem = useShopStore((s) => s.giftItem);
  const setGiftingMode = useShopStore((s) => s.setGiftingMode);
  const fetchRoom = useRoomStore((s) => s.fetchRoom);
  const checkMilestones = useGamificationStore((s) => s.checkMilestones);

  const [selectedCategory, setSelectedCategory] = useState("all");

  useEffect(() => {
    if (isOpen) {
      fetchShop();
      fetchBalance();
    }
  }, [isOpen, fetchShop, fetchBalance]);

  const filteredItems =
    selectedCategory === "all"
      ? catalog
      : catalog.filter((item) => item.category === selectedCategory);

  const handleBuy = async (itemId: string) => {
    if (isGifting && selectedRecipientId) {
      const result = await giftItem(itemId, selectedRecipientId);
      if (result) {
        toast.success(t("giftSent", { name: result.recipient_name }));
        fetchBalance();
      }
      return;
    }
    const result = await buyItem(itemId);
    if (result) {
      toast.success(t("purchaseSuccess"));
      fetchRoom();
      checkMilestones();
    }
  };

  const handleClose = () => {
    setGiftingMode(null);
    closeModal();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {isGifting ? (
              <Gift className="h-5 w-5 text-accent" />
            ) : (
              <ShoppingBag className="h-5 w-5 text-accent" />
            )}
            {isGifting ? t("buyAsGift") : t("title")}
          </DialogTitle>
          <DialogDescription className="flex items-center gap-2">
            {t("subtitle")}
            <EssenceBadge balance={essenceBalance.balance} size="sm" />
          </DialogDescription>
        </DialogHeader>

        {/* Gift toggle + partner selector */}
        <div className="space-y-2">
          <Button
            variant={isGifting ? "accent" : "outline"}
            size="xs"
            onClick={() => {
              if (isGifting) {
                setGiftingMode(null);
              } else {
                // Enter gift mode — store shows isGifting=true, no recipient selected yet
                useShopStore.setState({ isGifting: true, selectedRecipientId: null });
              }
            }}
          >
            <Gift className="h-3.5 w-3.5" />
            {t("buyAsGift")}
          </Button>
          {isGifting && <PartnerGiftSelector />}
        </div>

        {/* Category tabs */}
        <div className="flex gap-1 overflow-x-auto pb-1">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.key}
              className={cn(
                "flex items-center gap-1 rounded-full px-3 py-1 text-sm whitespace-nowrap transition-colors",
                selectedCategory === cat.key
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              )}
              onClick={() => setSelectedCategory(cat.key)}
            >
              <span>{cat.icon}</span>
              <span>{t(`category.${cat.key}`)}</span>
            </button>
          ))}
        </div>

        {/* Item grid */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : filteredItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
              <Package className="h-8 w-8 mb-2" />
              <p className="text-sm">{t("noItems")}</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-1">
              {filteredItems.map((item) => {
                const canAfford = essenceBalance.balance >= item.essence_cost;
                return (
                  <div
                    key={item.id}
                    className="rounded-xl border border-border bg-card p-3 flex flex-col gap-2"
                  >
                    {/* Item image */}
                    <div className="aspect-square rounded-lg bg-muted/50 flex items-center justify-center">
                      {item.image_url ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img
                          src={item.image_url}
                          alt={item.name}
                          className="w-full h-full object-contain p-2"
                        />
                      ) : (
                        <Package className="h-8 w-8 text-muted-foreground" />
                      )}
                    </div>

                    {/* Item info */}
                    <div className="flex-1">
                      <p className="text-sm font-medium truncate">{item.name}</p>
                      <div className="flex items-center gap-1 mt-1">
                        <Badge
                          className={cn("text-[10px]", TIER_COLORS[item.tier])}
                          variant="ghost"
                        >
                          {item.tier}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {item.size_w}x{item.size_h}
                        </span>
                      </div>
                    </div>

                    {/* Price + Buy/Gift */}
                    <Button
                      variant={canAfford ? "accent" : "outline"}
                      size="xs"
                      className="w-full"
                      disabled={
                        !canAfford ||
                        isPurchasing ||
                        !item.is_available ||
                        (isGifting && !selectedRecipientId)
                      }
                      onClick={() => handleBuy(item.id)}
                    >
                      {isPurchasing ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <>
                          {isGifting ? (
                            <Gift className="h-3 w-3" />
                          ) : (
                            <Sparkles className="h-3 w-3" />
                          )}
                          {item.essence_cost === 0 ? t("free") : item.essence_cost}
                        </>
                      )}
                    </Button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
