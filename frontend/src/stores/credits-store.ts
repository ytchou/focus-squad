import { create } from "zustand";

/**
 * Credit tiers from SPEC.md:
 * - free: 2 credits/week
 * - pro: 8 credits/week
 * - elite: 12 credits/week
 * - infinite: unlimited
 *
 * Note: Credits are NOT persisted to localStorage - they are always
 * fetched fresh from the server to ensure accuracy.
 */
export type CreditTier = "free" | "pro" | "elite" | "infinite";

const TIER_LIMITS: Record<CreditTier, number> = {
  free: 2,
  pro: 8,
  elite: 12,
  infinite: Infinity,
};

interface CreditsState {
  // Balance info
  balance: number;
  weeklyUsed: number;
  tier: CreditTier;

  // Refresh tracking
  refreshDate: string | null; // ISO date string

  // Computed
  weeklyLimit: number;
  creditsRemaining: number;

  // Actions
  setCredits: (balance: number, weeklyUsed: number) => void;
  setTier: (tier: CreditTier) => void;
  deductCredit: () => boolean;
  addCredits: (amount: number) => void;
  setRefreshDate: (date: string) => void;
  refreshWeeklyCredits: () => void;
}

export const useCreditsStore = create<CreditsState>()((set, get) => ({
  // Initial state
  balance: 0,
  weeklyUsed: 0,
  tier: "free",
  refreshDate: null,

  // Computed getters (these are recalculated on each access)
  get weeklyLimit() {
    return TIER_LIMITS[get().tier];
  },
  get creditsRemaining() {
    const state = get();
    return Math.max(0, state.balance - state.weeklyUsed);
  },

  // Actions
  setCredits: (balance, weeklyUsed) => set({ balance, weeklyUsed }),

  setTier: (tier) => set({ tier }),

  deductCredit: () => {
    const { balance } = get();
    if (balance > 0) {
      set((state) => ({
        balance: state.balance - 1,
        weeklyUsed: state.weeklyUsed + 1,
      }));
      return true;
    }
    return false;
  },

  addCredits: (amount) =>
    set((state) => ({
      balance: state.balance + amount,
    })),

  setRefreshDate: (date) => set({ refreshDate: date }),

  refreshWeeklyCredits: () => {
    const { tier } = get();
    const weeklyLimit = TIER_LIMITS[tier];
    set({
      balance: weeklyLimit,
      weeklyUsed: 0,
      refreshDate: new Date().toISOString(),
    });
  },
}));
