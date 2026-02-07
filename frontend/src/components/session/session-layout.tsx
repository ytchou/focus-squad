"use client";

import type { ReactNode } from "react";

interface SessionLayoutProps {
  header: ReactNode;
  children: ReactNode;
  controls: ReactNode;
}

/**
 * Main layout structure for the session page.
 * - Sticky header with phase badge and leave button
 * - Scrollable main content (timer, participants)
 * - Fixed bottom control bar
 */
export function SessionLayout({ header, children, controls }: SessionLayoutProps) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Sticky header */}
      {header}

      {/* Main content - scrollable, centered */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 pb-28">{children}</main>

      {/* Fixed bottom control bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-card border-t border-border px-4 py-4 pb-safe">
        <div className="max-w-2xl mx-auto">{controls}</div>
      </div>
    </div>
  );
}
