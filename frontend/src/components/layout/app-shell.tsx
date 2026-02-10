"use client";

import { useUIStore } from "@/stores";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { UpgradeModal } from "@/components/credits/upgrade-modal";
import { cn } from "@/lib/utils";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const isSidebarCollapsed = useUIStore((state) => state.isSidebarCollapsed);
  const activeModal = useUIStore((state) => state.activeModal);
  const closeModal = useUIStore((state) => state.closeModal);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <Sidebar />
      <main
        className={cn(
          "min-h-[calc(100vh-57px)] transition-all duration-300",
          // Mobile: no margin (sidebar overlays)
          "ml-0",
          // Desktop: margin based on sidebar state
          isSidebarCollapsed ? "md:ml-16" : "md:ml-64"
        )}
      >
        <div className="p-4 md:p-6">{children}</div>
      </main>
      <UpgradeModal isOpen={activeModal === "upgrade"} onClose={closeModal} />
    </div>
  );
}
