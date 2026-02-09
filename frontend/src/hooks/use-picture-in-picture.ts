"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { createElement } from "react";
import type { SessionPhase } from "@/stores/session-store";
import type { PiPParticipant } from "@/components/session/pip/pip-colors";
import { PiPMiniView } from "@/components/session/pip/pip-mini-view";
import { PiPCanvasRenderer } from "@/components/session/pip/pip-canvas-renderer";

type PiPStrategy = "document" | "canvas" | "none";

function detectStrategy(): PiPStrategy {
  if (typeof window === "undefined") return "none";
  if ("documentPictureInPicture" in window) return "document";
  if (document.pictureInPictureEnabled) return "canvas";
  return "none";
}

export interface UsePictureInPictureOptions {
  phase: SessionPhase;
  timeRemaining: number;
  participants: PiPParticipant[];
}

export interface UsePictureInPictureReturn {
  isPiPActive: boolean;
  isPiPSupported: boolean;
  togglePiP: () => void;
}

export function usePictureInPicture({
  phase,
  timeRemaining,
  participants,
}: UsePictureInPictureOptions): UsePictureInPictureReturn {
  const [isPiPActive, setIsPiPActive] = useState(false);
  const [strategy] = useState<PiPStrategy>(detectStrategy);

  const isTogglingRef = useRef(false);

  // Document PiP refs
  const pipWindowRef = useRef<Window | null>(null);
  const reactRootRef = useRef<Root | null>(null);

  // Canvas PiP refs
  const canvasRendererRef = useRef<PiPCanvasRenderer | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const updateIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Keep latest props in refs for use in intervals/callbacks
  const propsRef = useRef({ phase, timeRemaining, participants });
  useEffect(() => {
    propsRef.current = { phase, timeRemaining, participants };
  }, [phase, timeRemaining, participants]);

  // --- Cleanup helpers ---

  const cleanupDocumentPiP = useCallback(() => {
    if (reactRootRef.current) {
      reactRootRef.current.unmount();
      reactRootRef.current = null;
    }
    if (pipWindowRef.current) {
      try {
        pipWindowRef.current.close();
      } catch {
        // Window may already be closed
      }
      pipWindowRef.current = null;
    }
  }, []);

  const cleanupCanvasPiP = useCallback(() => {
    if (updateIntervalRef.current) {
      clearInterval(updateIntervalRef.current);
      updateIntervalRef.current = null;
    }
    if (videoRef.current && document.pictureInPictureElement === videoRef.current) {
      document.exitPictureInPicture().catch(() => {});
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
      videoRef.current.remove();
      videoRef.current = null;
    }
    if (canvasRendererRef.current) {
      canvasRendererRef.current.destroy();
      canvasRendererRef.current = null;
    }
  }, []);

  const cleanupAll = useCallback(() => {
    cleanupDocumentPiP();
    cleanupCanvasPiP();
    setIsPiPActive(false);
  }, [cleanupDocumentPiP, cleanupCanvasPiP]);

  // --- Document PiP ---

  const openDocumentPiP = useCallback(async () => {
    if (!window.documentPictureInPicture) return;

    const pipWindow = await window.documentPictureInPicture.requestWindow({
      width: 320,
      height: 180,
    });

    pipWindowRef.current = pipWindow;

    // Remove default margin/padding on PiP document body
    const style = pipWindow.document.createElement("style");
    style.textContent = "body { margin: 0; padding: 0; overflow: hidden; }";
    pipWindow.document.head.appendChild(style);

    // Create React root in PiP window
    const container = pipWindow.document.createElement("div");
    pipWindow.document.body.appendChild(container);
    const root = createRoot(container);
    reactRootRef.current = root;

    // Initial render
    const { phase: p, timeRemaining: t, participants: parts } = propsRef.current;
    root.render(createElement(PiPMiniView, { phase: p, timeRemaining: t, participants: parts }));

    // Listen for PiP window close
    pipWindow.addEventListener("pagehide", () => {
      cleanupDocumentPiP();
      setIsPiPActive(false);
    });

    setIsPiPActive(true);
  }, [cleanupDocumentPiP]);

  // --- Canvas Video PiP ---

  const openCanvasPiP = useCallback(async () => {
    const renderer = new PiPCanvasRenderer();
    canvasRendererRef.current = renderer;

    // Initial render
    renderer.render(propsRef.current);

    // Create video from canvas stream
    const canvas = renderer.getCanvas();
    const stream = canvas.captureStream(0); // 0 fps = manual frame push
    streamRef.current = stream;
    const video = document.createElement("video");
    video.srcObject = stream;
    video.muted = true;
    video.style.position = "fixed";
    video.style.top = "-9999px";
    video.style.left = "-9999px";
    document.body.appendChild(video);
    videoRef.current = video;

    await video.play();
    await video.requestPictureInPicture();

    // Update loop: redraw canvas every second and push frame
    updateIntervalRef.current = setInterval(() => {
      if (!canvasRendererRef.current) return;
      canvasRendererRef.current.render(propsRef.current);
      const track = stream.getVideoTracks()[0];
      if (track && "requestFrame" in track) {
        (track as unknown as { requestFrame: () => void }).requestFrame();
      }
    }, 1000);

    // Listen for PiP close
    video.addEventListener("leavepictureinpicture", () => {
      cleanupCanvasPiP();
      setIsPiPActive(false);
    });

    setIsPiPActive(true);
  }, [cleanupCanvasPiP]);

  // --- Update Document PiP on prop changes ---

  useEffect(() => {
    if (!isPiPActive || strategy !== "document" || !reactRootRef.current) return;
    reactRootRef.current.render(createElement(PiPMiniView, { phase, timeRemaining, participants }));
  }, [isPiPActive, strategy, phase, timeRemaining, participants]);

  // --- Toggle ---

  const togglePiP = useCallback(() => {
    if (isTogglingRef.current) return;
    isTogglingRef.current = true;

    const doToggle = async () => {
      try {
        if (isPiPActive) {
          cleanupAll();
          return;
        }

        if (strategy === "document") {
          await openDocumentPiP();
        } else if (strategy === "canvas") {
          await openCanvasPiP();
        }
      } catch (err) {
        console.error("PiP toggle failed:", err);
        cleanupAll();
      } finally {
        isTogglingRef.current = false;
      }
    };

    doToggle();
  }, [isPiPActive, strategy, cleanupAll, openDocumentPiP, openCanvasPiP]);

  // --- Auto-close on session end ---

  useEffect(() => {
    if (phase === "completed" && isPiPActive) {
      cleanupAll();
    }
  }, [phase, isPiPActive, cleanupAll]);

  // --- Cleanup on unmount ---

  useEffect(() => {
    return () => {
      cleanupAll();
    };
  }, [cleanupAll]);

  return {
    isPiPActive,
    isPiPSupported: strategy !== "none",
    togglePiP,
  };
}
