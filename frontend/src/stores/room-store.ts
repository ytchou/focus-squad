import { create } from "zustand";
import { api } from "@/lib/api/client";

// =============================================================================
// Types
// =============================================================================

export interface RoomPlacement {
  inventory_id: string;
  grid_x: number;
  grid_y: number;
  rotation: number;
}

export interface ShopItem {
  id: string;
  name: string;
  name_zh: string | null;
  description: string | null;
  description_zh: string | null;
  category: string;
  rarity: string;
  image_url: string | null;
  essence_cost: number;
  tier: string;
  size_w: number;
  size_h: number;
  attraction_tags: string[];
  is_available: boolean;
}

export interface InventoryItem {
  id: string;
  item_id: string;
  item: ShopItem | null;
  acquired_at: string;
  acquisition_type: string;
  gifted_by?: string | null;
  gifted_by_name?: string | null;
  gift_seen?: boolean;
}

export interface CompanionInfo {
  id: string;
  user_id: string;
  companion_type: string;
  is_starter: boolean;
  discovered_at: string | null;
  visit_scheduled_at: string | null;
  adopted_at: string | null;
}

export interface VisitorResult {
  companion_type: string;
  visit_scheduled_at: string;
}

export interface RoomState {
  user_id: string;
  room_type: string;
  layout: RoomPlacement[];
  active_companion: string | null;
  updated_at: string | null;
}

export interface RoomResponse {
  room: RoomState;
  inventory: InventoryItem[];
  companions: CompanionInfo[];
  visitors: VisitorResult[];
  essence_balance: number;
}

export interface PartnerRoomResponse {
  room: RoomState;
  inventory: InventoryItem[];
  companions: CompanionInfo[];
  owner_name: string;
  owner_username: string;
  owner_pixel_avatar_id: string | null;
}

export interface GiftNotification {
  inventory_item_id: string;
  item_name: string;
  item_name_zh: string | null;
  gifted_by_name: string;
  gift_message: string | null;
}

// =============================================================================
// Store
// =============================================================================

interface RoomStoreState {
  roomData: RoomResponse | null;
  isLoading: boolean;
  editMode: boolean;
  pendingLayout: RoomPlacement[];
  error: string | null;

  // Partner room viewing
  partnerRoom: PartnerRoomResponse | null;
  isPartnerRoomLoading: boolean;

  // Gift notifications
  unseenGifts: GiftNotification[];

  fetchRoom: () => Promise<RoomResponse | null>;
  saveLayout: () => Promise<void>;
  toggleEditMode: () => void;
  exitEditMode: () => void;
  addPlacement: (placement: RoomPlacement) => void;
  removePlacement: (inventoryId: string) => void;
  fetchPartnerRoom: (userId: string) => Promise<PartnerRoomResponse | null>;
  clearPartnerRoom: () => void;
  fetchUnseenGifts: () => Promise<GiftNotification[]>;
  markGiftsSeen: (ids: string[]) => Promise<void>;
  reset: () => void;
}

const initialState = {
  roomData: null as RoomResponse | null,
  isLoading: false,
  editMode: false,
  pendingLayout: [] as RoomPlacement[],
  error: null as string | null,
  partnerRoom: null as PartnerRoomResponse | null,
  isPartnerRoomLoading: false,
  unseenGifts: [] as GiftNotification[],
};

export const useRoomStore = create<RoomStoreState>()((set, get) => ({
  ...initialState,

  fetchRoom: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.get<RoomResponse>("/api/v1/room/");
      set({
        roomData: data,
        pendingLayout: data.room.layout,
        isLoading: false,
      });
      return data;
    } catch {
      set({ error: "Failed to load room", isLoading: false });
      return null;
    }
  },

  saveLayout: async () => {
    const { pendingLayout } = get();
    try {
      const updated = await api.put<RoomState>("/api/v1/room/layout", {
        placements: pendingLayout,
      });
      set((state) => ({
        roomData: state.roomData ? { ...state.roomData, room: updated } : null,
        editMode: false,
      }));
    } catch {
      set({ error: "Failed to save layout" });
    }
  },

  toggleEditMode: () =>
    set((state) => {
      if (state.editMode) {
        // Exiting edit mode — revert pending changes
        return {
          editMode: false,
          pendingLayout: state.roomData?.room.layout || [],
        };
      }
      return { editMode: true };
    }),

  exitEditMode: () =>
    set((state) => ({
      editMode: false,
      pendingLayout: state.roomData?.room.layout || [],
    })),

  addPlacement: (placement) =>
    set((state) => ({
      pendingLayout: [
        ...state.pendingLayout.filter((p) => p.inventory_id !== placement.inventory_id),
        placement,
      ],
    })),

  removePlacement: (inventoryId) =>
    set((state) => ({
      pendingLayout: state.pendingLayout.filter((p) => p.inventory_id !== inventoryId),
    })),

  fetchPartnerRoom: async (userId: string) => {
    set({ isPartnerRoomLoading: true, partnerRoom: null });
    try {
      const data = await api.get<PartnerRoomResponse>(`/api/v1/room/partner/${userId}`);
      set({ partnerRoom: data, isPartnerRoomLoading: false });
      return data;
    } catch {
      set({ isPartnerRoomLoading: false });
      return null;
    }
  },

  clearPartnerRoom: () => set({ partnerRoom: null }),

  fetchUnseenGifts: async () => {
    try {
      const data = await api.get<GiftNotification[]>("/api/v1/room/gifts");
      set({ unseenGifts: data });
      return data;
    } catch {
      return [];
    }
  },

  markGiftsSeen: async (ids: string[]) => {
    try {
      await api.post("/api/v1/room/gifts/seen", { inventory_ids: ids });
      set({ unseenGifts: [] });
    } catch {
      // Non-critical
    }
  },

  reset: () => set(initialState),
}));
