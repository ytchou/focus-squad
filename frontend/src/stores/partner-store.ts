import { create } from "zustand";
import { api } from "@/lib/api/client";

export interface PartnerInfo {
  partnership_id: string;
  user_id: string;
  username: string;
  display_name: string | null;
  avatar_config: Record<string, unknown>;
  pixel_avatar_id: string | null;
  study_interests: string[];
  reliability_score: string | null;
  last_session_together: string | null;
}

export interface PartnerRequestInfo {
  partnership_id: string;
  user_id: string;
  username: string;
  display_name: string | null;
  avatar_config: Record<string, unknown>;
  pixel_avatar_id: string | null;
  direction: "incoming" | "outgoing";
  created_at: string;
}

export interface InvitationInfo {
  invitation_id: string;
  session_id: string;
  inviter_id: string;
  inviter_name: string;
  session_start_time: string;
  session_mode: string;
  status: string;
}

export interface UserSearchResult {
  user_id: string;
  username: string;
  display_name: string | null;
  avatar_config: Record<string, unknown>;
  pixel_avatar_id: string | null;
  study_interests: string[];
  partnership_status: string | null;
}

interface PartnerState {
  partners: PartnerInfo[];
  pendingRequests: PartnerRequestInfo[];
  pendingInvitations: InvitationInfo[];
  searchResults: UserSearchResult[];
  isLoading: boolean;
  isSearching: boolean;
  error: string | null;

  fetchPartners: () => Promise<void>;
  fetchRequests: () => Promise<void>;
  fetchInvitations: () => Promise<void>;
  sendRequest: (addresseeId: string) => Promise<void>;
  respondToRequest: (partnershipId: string, accept: boolean) => Promise<void>;
  removePartner: (partnershipId: string) => Promise<void>;
  searchUsers: (query: string) => Promise<void>;
  respondToInvitation: (sessionId: string, invitationId: string, accept: boolean) => Promise<void>;
  clearSearch: () => void;
  reset: () => void;
}

const initialState = {
  partners: [] as PartnerInfo[],
  pendingRequests: [] as PartnerRequestInfo[],
  pendingInvitations: [] as InvitationInfo[],
  searchResults: [] as UserSearchResult[],
  isLoading: false,
  isSearching: false,
  error: null as string | null,
};

export const usePartnerStore = create<PartnerState>()((set, get) => ({
  ...initialState,

  fetchPartners: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.get<{ partners: PartnerInfo[]; total: number }>("/api/v1/partners/");
      set({ partners: data.partners, isLoading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load partners";
      set({ error: message, isLoading: false });
    }
  },

  fetchRequests: async () => {
    try {
      const data = await api.get<{ requests: PartnerRequestInfo[] }>("/api/v1/partners/requests");
      set({ pendingRequests: data.requests });
    } catch {
      // Non-critical — silent fail
    }
  },

  fetchInvitations: async () => {
    try {
      const data = await api.get<{ invitations: InvitationInfo[] }>("/api/v1/sessions/invitations");
      set({ pendingInvitations: data.invitations });
    } catch {
      // Non-critical — silent fail
    }
  },

  sendRequest: async (addresseeId) => {
    set({ error: null });
    try {
      await api.post("/api/v1/partners/request", {
        addressee_id: addresseeId,
      });
      // Refresh requests list
      await get().fetchRequests();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to send request";
      set({ error: message });
      throw err;
    }
  },

  respondToRequest: async (partnershipId, accept) => {
    set({ error: null });
    try {
      await api.post(`/api/v1/partners/request/${partnershipId}/respond`, {
        accept,
      });
      // Refresh both lists
      await Promise.all([get().fetchPartners(), get().fetchRequests()]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to respond to request";
      set({ error: message });
      throw err;
    }
  },

  removePartner: async (partnershipId) => {
    set({ error: null });
    try {
      await api.delete(`/api/v1/partners/${partnershipId}`);
      set({
        partners: get().partners.filter((p) => p.partnership_id !== partnershipId),
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to remove partner";
      set({ error: message });
      throw err;
    }
  },

  searchUsers: async (query) => {
    if (!query.trim()) {
      set({ searchResults: [] });
      return;
    }
    set({ isSearching: true });
    try {
      const data = await api.get<{ users: UserSearchResult[] }>(
        `/api/v1/partners/search?q=${encodeURIComponent(query)}`
      );
      set({ searchResults: data.users, isSearching: false });
    } catch {
      set({ searchResults: [], isSearching: false });
    }
  },

  respondToInvitation: async (sessionId, invitationId, accept) => {
    set({ error: null });
    try {
      await api.post(`/api/v1/sessions/${sessionId}/invite/respond`, {
        invitation_id: invitationId,
        accept,
      });
      set({
        pendingInvitations: get().pendingInvitations.filter(
          (inv) => inv.invitation_id !== invitationId
        ),
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to respond to invitation";
      set({ error: message });
      throw err;
    }
  },

  clearSearch: () => set({ searchResults: [] }),

  reset: () => set(initialState),
}));
