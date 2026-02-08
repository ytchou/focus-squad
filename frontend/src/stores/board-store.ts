/**
 * Session Board store for reflections and ephemeral chat.
 *
 * Manages the message stream displayed during a live session.
 * Reflections are persisted via API; chat messages are ephemeral
 * (LiveKit data channels only).
 */
import { create } from "zustand";
import { api } from "@/lib/api/client";

// =============================================================================
// Types
// =============================================================================

export type MessageType = "reflection" | "chat" | "system";
export type ReflectionPhase = "setup" | "break" | "social";

export interface BoardMessage {
  id: string;
  type: MessageType;
  userId: string;
  displayName: string;
  content: string;
  timestamp: number;
  phase?: ReflectionPhase;
}

interface ReflectionApiResponse {
  id: string;
  session_id: string;
  user_id: string;
  display_name: string | null;
  phase: ReflectionPhase;
  content: string;
  created_at: string;
  updated_at: string;
}

interface SessionReflectionsApiResponse {
  reflections: ReflectionApiResponse[];
}

// =============================================================================
// Store
// =============================================================================

interface BoardState {
  messages: BoardMessage[];
  isDrawerOpen: boolean;
  unreadCount: number;
  isSaving: boolean;

  addMessage: (message: BoardMessage) => void;
  saveReflection: (
    sessionId: string,
    phase: ReflectionPhase,
    content: string,
    userId: string,
    displayName: string
  ) => Promise<void>;
  loadSessionReflections: (sessionId: string) => Promise<void>;
  setDrawerOpen: (open: boolean) => void;
  incrementUnread: () => void;
  resetUnread: () => void;
  reset: () => void;
}

const initialState = {
  messages: [] as BoardMessage[],
  isDrawerOpen: false,
  unreadCount: 0,
  isSaving: false,
};

export const useBoardStore = create<BoardState>()((set, get) => ({
  ...initialState,

  addMessage: (message) => {
    set((state) => {
      // Deduplicate by id
      if (state.messages.some((m) => m.id === message.id)) {
        return state;
      }
      return { messages: [...state.messages, message] };
    });
  },

  saveReflection: async (sessionId, phase, content, userId, displayName) => {
    set({ isSaving: true });

    const message: BoardMessage = {
      id: `reflection-${userId}-${phase}-${Date.now()}`,
      type: "reflection",
      userId,
      displayName,
      content,
      timestamp: Date.now(),
      phase,
    };

    // Optimistic: add to local stream immediately
    get().addMessage(message);

    try {
      // Persist to backend
      const result = await api.post<ReflectionApiResponse>(`/sessions/${sessionId}/reflections`, {
        phase,
        content,
      });
      // Update the message id with the server-assigned one
      set((state) => ({
        messages: state.messages.map((m) => (m.id === message.id ? { ...m, id: result.id } : m)),
      }));
    } catch (err) {
      console.error("Failed to persist reflection:", err);
      // Reflection was still broadcast via data channel - graceful degradation
    } finally {
      set({ isSaving: false });
    }
  },

  loadSessionReflections: async (sessionId) => {
    try {
      const data = await api.get<SessionReflectionsApiResponse>(
        `/sessions/${sessionId}/reflections`
      );

      const messages: BoardMessage[] = data.reflections.map((r) => ({
        id: r.id,
        type: "reflection" as const,
        userId: r.user_id,
        displayName: r.display_name || "User",
        content: r.content,
        timestamp: new Date(r.created_at).getTime(),
        phase: r.phase,
      }));

      // Merge with existing messages (avoid duplicates by id and content match)
      set((state) => {
        const existingIds = new Set(state.messages.map((m) => m.id));
        // Also match by user+phase+content to catch temp-ID vs server-ID dupes
        const existingContentKeys = new Set(
          state.messages
            .filter((m) => m.type === "reflection")
            .map((m) => `${m.userId}-${m.phase}-${m.content}`)
        );
        const newMessages = messages.filter(
          (m) =>
            !existingIds.has(m.id) &&
            !(
              m.type === "reflection" &&
              existingContentKeys.has(`${m.userId}-${m.phase}-${m.content}`)
            )
        );
        return {
          messages: [...newMessages, ...state.messages].sort((a, b) => a.timestamp - b.timestamp),
        };
      });
    } catch (err) {
      console.error("Failed to load session reflections:", err);
    }
  },

  setDrawerOpen: (open) => {
    set({ isDrawerOpen: open });
    if (open) {
      set({ unreadCount: 0 });
    }
  },

  incrementUnread: () => {
    set((state) => ({ unreadCount: state.unreadCount + 1 }));
  },

  resetUnread: () => set({ unreadCount: 0 }),

  reset: () => set(initialState),
}));
