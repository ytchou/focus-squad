import { describe, it, expect, beforeEach } from "vitest";
import { useCreditsStore } from "../credits-store";

describe("Credits Store", () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useCreditsStore.setState({
      balance: 2,
      weeklyUsed: 0,
      tier: "free",
      refreshDate: null,
    });
  });

  describe("setCredits", () => {
    it("should update balance and weeklyUsed", () => {
      const store = useCreditsStore.getState();
      store.setCredits(5, 3);

      const state = useCreditsStore.getState();
      expect(state.balance).toBe(5);
      expect(state.weeklyUsed).toBe(3);
    });
  });

  describe("setTier", () => {
    it("should update tier", () => {
      const store = useCreditsStore.getState();
      store.setTier("pro");

      const state = useCreditsStore.getState();
      expect(state.tier).toBe("pro");
    });
  });

  describe("deductCredit", () => {
    it("should deduct credit and increment weeklyUsed when balance > 0", () => {
      const store = useCreditsStore.getState();
      const result = store.deductCredit();

      const state = useCreditsStore.getState();
      expect(result).toBe(true);
      expect(state.balance).toBe(1);
      expect(state.weeklyUsed).toBe(1);
    });

    it("should not deduct when balance is 0", () => {
      useCreditsStore.setState({ balance: 0 });
      const store = useCreditsStore.getState();
      const result = store.deductCredit();

      const state = useCreditsStore.getState();
      expect(result).toBe(false);
      expect(state.balance).toBe(0);
      expect(state.weeklyUsed).toBe(0);
    });

    it("should deduct multiple credits correctly", () => {
      useCreditsStore.setState({ balance: 5, weeklyUsed: 0 });
      const store = useCreditsStore.getState();

      store.deductCredit();
      store.deductCredit();
      store.deductCredit();

      const state = useCreditsStore.getState();
      expect(state.balance).toBe(2);
      expect(state.weeklyUsed).toBe(3);
    });
  });

  describe("addCredits", () => {
    it("should add credits to balance", () => {
      const store = useCreditsStore.getState();
      store.addCredits(3);

      const state = useCreditsStore.getState();
      expect(state.balance).toBe(5);
    });
  });

  describe("refreshWeeklyCredits", () => {
    it("should reset credits based on tier (free)", () => {
      useCreditsStore.setState({ balance: 0, weeklyUsed: 2, tier: "free" });
      const store = useCreditsStore.getState();
      store.refreshWeeklyCredits();

      const state = useCreditsStore.getState();
      expect(state.balance).toBe(2);
      expect(state.weeklyUsed).toBe(0);
      expect(state.refreshDate).toBeTruthy();
    });

    it("should reset credits based on tier (pro)", () => {
      useCreditsStore.setState({ balance: 0, weeklyUsed: 8, tier: "pro" });
      const store = useCreditsStore.getState();
      store.refreshWeeklyCredits();

      const state = useCreditsStore.getState();
      expect(state.balance).toBe(8);
      expect(state.weeklyUsed).toBe(0);
    });

    it("should reset credits based on tier (elite)", () => {
      useCreditsStore.setState({ balance: 0, weeklyUsed: 12, tier: "elite" });
      const store = useCreditsStore.getState();
      store.refreshWeeklyCredits();

      const state = useCreditsStore.getState();
      expect(state.balance).toBe(12);
      expect(state.weeklyUsed).toBe(0);
    });
  });
});
