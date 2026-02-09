"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  BookOpen,
  Users,
  Clock,
  Trophy,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUIStore } from "@/stores";
import { useDebugBanner } from "@/hooks/use-debug-banner";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", icon: Home, label: "Home" },
  { href: "/diary", icon: BookOpen, label: "Diary" },
  { href: "/sessions", icon: Clock, label: "Sessions" },
  { href: "/find-table", icon: Users, label: "Find Table" },
  { href: "/collection", icon: Trophy, label: "Collection" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();
  const isSidebarOpen = useUIStore((state) => state.isSidebarOpen);
  const isSidebarCollapsed = useUIStore((state) => state.isSidebarCollapsed);
  const setSidebarCollapsed = useUIStore((state) => state.setSidebarCollapsed);
  const { isVisible: isDebugBannerVisible } = useDebugBanner();

  // On mobile, sidebar is controlled by isSidebarOpen (overlay)
  // On desktop, sidebar can be collapsed but is always visible
  const isCollapsed = isSidebarCollapsed;

  // Header is 57px, debug banner adds 32px when visible
  const topOffset = isDebugBannerVisible ? "top-[89px]" : "top-[57px]";
  const heightOffset = isDebugBannerVisible ? "h-[calc(100vh-89px)]" : "h-[calc(100vh-57px)]";

  return (
    <>
      {/* Mobile overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => useUIStore.getState().toggleSidebar()}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          `fixed left-0 ${topOffset} z-40 ${heightOffset} bg-surface border-r border-border transition-all duration-300`,
          // Mobile: slide in/out
          isSidebarOpen ? "translate-x-0" : "-translate-x-full",
          // Desktop: always visible, can collapse
          "md:translate-x-0",
          isCollapsed ? "md:w-16" : "md:w-64",
          // Mobile width
          "w-64"
        )}
      >
        <nav className="flex h-full flex-col p-4">
          <ul className="flex-1 space-y-1">
            {navItems.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));

              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                    title={isCollapsed ? item.label : undefined}
                  >
                    <item.icon className="h-5 w-5 shrink-0" />
                    {!isCollapsed && <span>{item.label}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>

          {/* Collapse toggle (desktop only) */}
          <div className="hidden border-t border-border pt-4 md:block">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarCollapsed(!isCollapsed)}
              className="w-full justify-center"
            >
              {isCollapsed ? (
                <ChevronRight className="h-4 w-4" />
              ) : (
                <>
                  <ChevronLeft className="h-4 w-4" />
                  <span className="ml-2">Collapse</span>
                </>
              )}
            </Button>
          </div>
        </nav>
      </aside>
    </>
  );
}
