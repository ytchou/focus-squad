import { describe, it, expect, beforeEach, vi, type Mock } from "vitest";
import { useShopStore } from "../shop-store";
import { api } from "@/lib/api/client";

vi.mock("@/lib/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("Shop Store", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    useShopStore.setState({
      catalog: [],
      inventory: [],
      essenceBalance: { balance: 100, total_earned: 100, total_spent: 0 },
      isLoading: false,
      isPurchasing: false,
      error: null,
      isGifting: false,
      selectedRecipientId: null,
    });
  });

  describe("giftItem", () => {
    it("should use balance from response directly without extra API calls", async () => {
      const mockBalance = { balance: 90, total_earned: 100, total_spent: 10 };
      const mockGiftResponse = {
        inventory_item_id: "inv-123",
        item_name: "Cozy Lamp",
        recipient_name: "Friend",
        essence_spent: 10,
        balance: mockBalance,
      };

      (api.post as Mock).mockResolvedValueOnce(mockGiftResponse);

      const store = useShopStore.getState();
      const result = await store.giftItem("item-1", "recipient-123", "Enjoy!");

      expect(result).toEqual(mockGiftResponse);
      expect(api.post).toHaveBeenCalledWith("/api/v1/essence/gift", {
        item_id: "item-1",
        recipient_id: "recipient-123",
        gift_message: "Enjoy!",
      });

      // No extra api.get calls — balance comes from response
      expect(api.get).not.toHaveBeenCalled();

      // Verify state updated from response
      const state = useShopStore.getState();
      expect(state.essenceBalance).toEqual(mockBalance);
      expect(state.isPurchasing).toBe(false);
      expect(state.isGifting).toBe(false);
    });

    it("should handle gift failure gracefully", async () => {
      (api.post as Mock).mockRejectedValueOnce(new Error("Network error"));

      const store = useShopStore.getState();
      const result = await store.giftItem("item-1", "recipient-123");

      expect(result).toBeNull();
      const state = useShopStore.getState();
      expect(state.error).toBe("Gift failed");
      expect(state.isPurchasing).toBe(false);
      expect(state.isGifting).toBe(false);
      expect(state.selectedRecipientId).toBeNull();
    });
  });

  describe("buyItem", () => {
    it("should use balance from response and only fetch inventory", async () => {
      const mockItem = { id: "inv-123", item_id: "item-1" };
      const mockBalance = { balance: 90, total_earned: 100, total_spent: 10 };
      const mockInventory = [mockItem];

      // buyItem now returns PurchaseResponse with balance included
      (api.post as Mock).mockResolvedValueOnce({
        item: mockItem,
        balance: mockBalance,
        inventory_count: 1,
      });
      // Only fetchInventory is called (balance comes from response)
      (api.get as Mock).mockResolvedValueOnce(mockInventory);

      const store = useShopStore.getState();
      const result = await store.buyItem("item-1");

      expect(result).toEqual(mockItem);
      // Only 1 api.get call (inventory), not 2 — balance from response
      expect(api.get).toHaveBeenCalledTimes(1);
      expect(api.get).toHaveBeenCalledWith("/api/v1/essence/inventory");

      const state = useShopStore.getState();
      expect(state.essenceBalance).toEqual(mockBalance);
    });
  });

  describe("setGiftingMode", () => {
    it("should enable gifting mode with recipient", () => {
      const store = useShopStore.getState();
      store.setGiftingMode("recipient-123");

      const state = useShopStore.getState();
      expect(state.isGifting).toBe(true);
      expect(state.selectedRecipientId).toBe("recipient-123");
    });

    it("should disable gifting mode when null", () => {
      useShopStore.setState({ isGifting: true, selectedRecipientId: "old-id" });
      const store = useShopStore.getState();
      store.setGiftingMode(null);

      const state = useShopStore.getState();
      expect(state.isGifting).toBe(false);
      expect(state.selectedRecipientId).toBeNull();
    });
  });

  describe("fetchShop", () => {
    it("should fetch shop catalog successfully", async () => {
      const mockCatalog = [
        { id: "item-1", name: "Lamp", price: 10 },
        { id: "item-2", name: "Chair", price: 20 },
      ];
      (api.get as Mock).mockResolvedValueOnce(mockCatalog);

      const store = useShopStore.getState();
      await store.fetchShop();

      const state = useShopStore.getState();
      expect(state.catalog).toEqual(mockCatalog);
      expect(state.isLoading).toBe(false);
      expect(api.get).toHaveBeenCalledWith("/api/v1/essence/shop");
    });

    it("should fetch shop with category filter", async () => {
      const mockCatalog = [{ id: "item-1", name: "Lamp" }];
      (api.get as Mock).mockResolvedValueOnce(mockCatalog);

      const store = useShopStore.getState();
      await store.fetchShop("furniture");

      expect(api.get).toHaveBeenCalledWith("/api/v1/essence/shop?category=furniture");
    });

    it("should fetch shop with tier filter", async () => {
      const mockCatalog = [{ id: "item-1", name: "Rare Lamp" }];
      (api.get as Mock).mockResolvedValueOnce(mockCatalog);

      const store = useShopStore.getState();
      await store.fetchShop(undefined, "rare");

      expect(api.get).toHaveBeenCalledWith("/api/v1/essence/shop?tier=rare");
    });

    it("should fetch shop with both filters", async () => {
      const mockCatalog = [{ id: "item-1", name: "Rare Furniture" }];
      (api.get as Mock).mockResolvedValueOnce(mockCatalog);

      const store = useShopStore.getState();
      await store.fetchShop("furniture", "rare");

      expect(api.get).toHaveBeenCalledWith("/api/v1/essence/shop?category=furniture&tier=rare");
    });

    it("should handle fetch shop failure", async () => {
      (api.get as Mock).mockRejectedValueOnce(new Error("Network error"));

      const store = useShopStore.getState();
      await store.fetchShop();

      const state = useShopStore.getState();
      expect(state.error).toBe("Failed to load shop");
      expect(state.isLoading).toBe(false);
    });
  });

  describe("fetchInventory", () => {
    it("should fetch inventory successfully", async () => {
      const mockInventory = [{ id: "inv-1", item_id: "item-1" }];
      (api.get as Mock).mockResolvedValueOnce(mockInventory);

      const store = useShopStore.getState();
      await store.fetchInventory();

      const state = useShopStore.getState();
      expect(state.inventory).toEqual(mockInventory);
    });

    it("should handle fetch inventory failure", async () => {
      (api.get as Mock).mockRejectedValueOnce(new Error("Network error"));

      const store = useShopStore.getState();
      await store.fetchInventory();

      const state = useShopStore.getState();
      expect(state.error).toBe("Failed to load inventory");
    });
  });

  describe("fetchBalance", () => {
    it("should fetch balance successfully", async () => {
      const mockBalance = { balance: 50, total_earned: 100, total_spent: 50 };
      (api.get as Mock).mockResolvedValueOnce(mockBalance);

      const store = useShopStore.getState();
      await store.fetchBalance();

      const state = useShopStore.getState();
      expect(state.essenceBalance).toEqual(mockBalance);
    });

    it("should handle fetch balance failure", async () => {
      (api.get as Mock).mockRejectedValueOnce(new Error("Network error"));

      const store = useShopStore.getState();
      await store.fetchBalance();

      const state = useShopStore.getState();
      expect(state.error).toBe("Failed to load balance");
    });
  });

  describe("buyItem error handling", () => {
    it("should handle buy failure gracefully", async () => {
      (api.post as Mock).mockRejectedValueOnce(new Error("Network error"));

      const store = useShopStore.getState();
      const result = await store.buyItem("item-1");

      expect(result).toBeNull();
      const state = useShopStore.getState();
      expect(state.error).toBe("Purchase failed");
      expect(state.isPurchasing).toBe(false);
    });
  });

  describe("reset", () => {
    it("should reset store to initial state", () => {
      // Set some non-initial state
      useShopStore.setState({
        catalog: [{ id: "item-1" }] as never,
        inventory: [{ id: "inv-1" }] as never,
        essenceBalance: { balance: 500, total_earned: 600, total_spent: 100 },
        isLoading: true,
        isPurchasing: true,
        error: "Some error",
        isGifting: true,
        selectedRecipientId: "recipient-123",
      });

      const store = useShopStore.getState();
      store.reset();

      const state = useShopStore.getState();
      expect(state.catalog).toEqual([]);
      expect(state.inventory).toEqual([]);
      expect(state.essenceBalance).toEqual({ balance: 0, total_earned: 0, total_spent: 0 });
      expect(state.isLoading).toBe(false);
      expect(state.isPurchasing).toBe(false);
      expect(state.error).toBeNull();
      expect(state.isGifting).toBe(false);
      expect(state.selectedRecipientId).toBeNull();
    });
  });
});
