import { create } from "zustand";

export type NotificationType = "success" | "error" | "warning" | "info";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  duration?: number; // ms, 0 = persistent
  createdAt: Date;
}

interface NotificationsState {
  notifications: Notification[];
  unreadCount: number;

  // Actions
  addNotification: (notification: Omit<Notification, "id" | "createdAt">) => string;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  markAllRead: () => void;
}

export const useNotificationsStore = create<NotificationsState>((set, get) => ({
  notifications: [],
  unreadCount: 0,

  addNotification: (notification) => {
    const id = crypto.randomUUID();
    const newNotification: Notification = {
      ...notification,
      id,
      createdAt: new Date(),
    };

    set((state) => ({
      notifications: [newNotification, ...state.notifications],
      unreadCount: state.unreadCount + 1,
    }));

    // Auto-remove after duration (default 5 seconds)
    const duration = notification.duration ?? 5000;
    if (duration > 0) {
      setTimeout(() => {
        get().removeNotification(id);
      }, duration);
    }

    return id;
  },

  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  clearAll: () => set({ notifications: [], unreadCount: 0 }),

  markAllRead: () => set({ unreadCount: 0 }),
}));

// Helper hook for common notification patterns
export const useNotify = () => {
  const addNotification = useNotificationsStore((state) => state.addNotification);

  return {
    success: (title: string, message?: string) =>
      addNotification({ type: "success", title, message }),
    error: (title: string, message?: string) =>
      addNotification({ type: "error", title, message, duration: 0 }), // Errors persist
    warning: (title: string, message?: string) =>
      addNotification({ type: "warning", title, message }),
    info: (title: string, message?: string) =>
      addNotification({ type: "info", title, message }),
  };
};
