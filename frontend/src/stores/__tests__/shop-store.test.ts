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
    vi.clearAllMocks();
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
    it("should call both fetchBalance and fetchInventory after gifting", async () => {
      const mockGiftResponse = {
        inventory_item_id: "inv-123",
        item_name: "Cozy Lamp",
        recipient_name: "Friend",
        essence_spent: 10,
      };
      const mockBalance = { balance: 90, total_earned: 100, total_spent: 10 };
      const mockInventory = [{ id: "inv-456", item_id: "item-1" }];

      (api.post as Mock).mockResolvedValueOnce(mockGiftResponse);
      (api.get as Mock)
        .mockResolvedValueOnce(mockBalance) // fetchBalance
        .mockResolvedValueOnce(mockInventory); // fetchInventory

      const store = useShopStore.getState();
      const result = await store.giftItem("item-1", "recipient-123", "Enjoy!");

      expect(result).toEqual(mockGiftResponse);
      expect(api.post).toHaveBeenCalledWith("/api/v1/essence/gift", {
        item_id: "item-1",
        recipient_id: "recipient-123",
        gift_message: "Enjoy!",
      });

      // Verify both fetchBalance AND fetchInventory were called
      expect(api.get).toHaveBeenCalledTimes(2);
      expect(api.get).toHaveBeenCalledWith("/api/v1/essence/balance");
      expect(api.get).toHaveBeenCalledWith("/api/v1/essence/inventory");

      // Verify state updated
      const state = useShopStore.getState();
      expect(state.essenceBalance).toEqual(mockBalance);
      expect(state.inventory).toEqual(mockInventory);
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
    });
  });

  describe("buyItem", () => {
    it("should call both fetchBalance and fetchInventory after purchase", async () => {
      const mockItem = { id: "inv-123", item_id: "item-1" };
      const mockBalance = { balance: 90, total_earned: 100, total_spent: 10 };
      const mockInventory = [mockItem];

      (api.post as Mock).mockResolvedValueOnce(mockItem);
      (api.get as Mock).mockResolvedValueOnce(mockBalance).mockResolvedValueOnce(mockInventory);

      const store = useShopStore.getState();
      const result = await store.buyItem("item-1");

      expect(result).toEqual(mockItem);
      expect(api.get).toHaveBeenCalledTimes(2);
      expect(api.get).toHaveBeenCalledWith("/api/v1/essence/balance");
      expect(api.get).toHaveBeenCalledWith("/api/v1/essence/inventory");
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
});
