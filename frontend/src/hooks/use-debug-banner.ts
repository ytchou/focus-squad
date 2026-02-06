"use client";

import { useSyncExternalStore, useCallback } from "react";

const DISMISS_KEY = "focus-squad-debug-banner-dismissed";
const STORAGE_CHANGE_EVENT = "debug-banner-storage-change";

function getIsDismissed() {
  if (typeof window === "undefined") return true;
  return localStorage.getItem(DISMISS_KEY) === "true";
}

function subscribeToStorage(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(STORAGE_CHANGE_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(STORAGE_CHANGE_EVENT, callback);
  };
}

export function useDebugBanner() {
  const isDismissed = useSyncExternalStore(subscribeToStorage, getIsDismissed, () => true);

  const isDev = process.env.NODE_ENV === "development";
  const isVisible = isDev && !isDismissed;

  const setDismissed = useCallback((value: boolean) => {
    if (value) {
      localStorage.setItem(DISMISS_KEY, "true");
    } else {
      localStorage.removeItem(DISMISS_KEY);
    }
    window.dispatchEvent(new Event(STORAGE_CHANGE_EVENT));
  }, []);

  return {
    isDev,
    isDismissed,
    isVisible,
    setDismissed,
    bannerHeight: isVisible ? "h-8" : "",
    topOffset: isVisible ? "top-8" : "top-0",
  };
}
