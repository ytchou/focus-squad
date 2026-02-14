import { create } from "zustand";
import { api } from "@/lib/api/client";
import type { ShopItem, InventoryItem } from "./room-store";

// =============================================================================
// Types
// =============================================================================

export interface EssenceBalance {
  balance: number;
  total_earned: number;
  total_spent: number;
}

// =============================================================================
// Gift response
// =============================================================================

export interface PurchaseResponse {
  item: InventoryItem;
  balance: EssenceBalance;
  inventory_count: number;
}

export interface GiftPurchaseResponse {
  inventory_item_id: string;
  item_name: string;
  recipient_name: string;
  essence_spent: number;
  balance: EssenceBalance | null;
}

// =============================================================================
// Store
// =============================================================================

interface ShopStoreState {
  catalog: ShopItem[];
  inventory: InventoryItem[];
  essenceBalance: EssenceBalance;
  isLoading: boolean;
  isPurchasing: boolean;
  error: string | null;

  // Gift mode
  isGifting: boolean;
  selectedRecipientId: string | null;

  fetchShop: (category?: string, tier?: string) => Promise<void>;
  fetchInventory: () => Promise<void>;
  fetchBalance: () => Promise<void>;
  buyItem: (itemId: string) => Promise<InventoryItem | null>;
  giftItem: (
    itemId: string,
    recipientId: string,
    message?: string
  ) => Promise<GiftPurchaseResponse | null>;
  setGiftingMode: (recipientId: string | null) => void;
  reset: () => void;
}

const initialState = {
  catalog: [] as ShopItem[],
  inventory: [] as InventoryItem[],
  essenceBalance: { balance: 0, total_earned: 0, total_spent: 0 } as EssenceBalance,
  isLoading: false,
  isPurchasing: false,
  error: null as string | null,
  isGifting: false,
  selectedRecipientId: null as string | null,
};

export const useShopStore = create<ShopStoreState>()((set, get) => ({
  ...initialState,

  fetchShop: async (category?: string, tier?: string) => {
    set({ isLoading: true, error: null });
    try {
      const params = new URLSearchParams();
      if (category) params.append("category", category);
      if (tier) params.append("tier", tier);
      const query = params.toString();
      const url = query ? `/api/v1/essence/shop?${query}` : "/api/v1/essence/shop";
      const data = await api.get<ShopItem[]>(url);
      set({ catalog: data, isLoading: false });
    } catch {
      set({ error: "Failed to load shop", isLoading: false });
    }
  },

  fetchInventory: async () => {
    try {
      const data = await api.get<InventoryItem[]>("/api/v1/essence/inventory");
      set({ inventory: data });
    } catch {
      set({ error: "Failed to load inventory" });
    }
  },

  fetchBalance: async () => {
    try {
      const data = await api.get<EssenceBalance>("/api/v1/essence/balance");
      set({ essenceBalance: data });
    } catch {
      set({ error: "Failed to load balance" });
    }
  },

  buyItem: async (itemId: string) => {
    set({ isPurchasing: true, error: null });
    try {
      const response = await api.post<PurchaseResponse>("/api/v1/essence/buy", {
        item_id: itemId,
      });
      // Use enriched response directly instead of extra round-trips
      set({
        essenceBalance: response.balance,
        isPurchasing: false,
      });
      // Refresh inventory to get full list (response only has the new item)
      await get().fetchInventory();
      return response.item;
    } catch {
      set({ error: "Purchase failed", isPurchasing: false });
      return null;
    }
  },

  giftItem: async (itemId: string, recipientId: string, message?: string) => {
    set({ isPurchasing: true, error: null });
    try {
      const result = await api.post<GiftPurchaseResponse>("/api/v1/essence/gift", {
        item_id: itemId,
        recipient_id: recipientId,
        gift_message: message || null,
      });
      // Use balance from response directly instead of extra round-trip
      const updates: Partial<ShopStoreState> = {
        isPurchasing: false,
        isGifting: false,
        selectedRecipientId: null,
      };
      if (result.balance) {
        updates.essenceBalance = result.balance;
      }
      set(updates);
      return result;
    } catch {
      set({
        error: "Gift failed",
        isPurchasing: false,
        isGifting: false,
        selectedRecipientId: null,
      });
      return null;
    }
  },

  setGiftingMode: (recipientId: string | null) =>
    set({
      isGifting: recipientId !== null,
      selectedRecipientId: recipientId || null,
    }),

  reset: () => set(initialState),
}));
