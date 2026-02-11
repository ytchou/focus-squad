"use client";

import Link from "next/link";
import { Menu, Bell, User, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CreditBadge } from "@/components/ui/credit-badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useUIStore, useUserStore, useCreditsStore } from "@/stores";
import { useDebugBanner } from "@/hooks/use-debug-banner";

export function Header() {
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);
  const user = useUserStore((state) => state.user);
  const openModal = useUIStore((state) => state.openModal);
  const credits = useCreditsStore((state) => state.balance);
  const tier = useCreditsStore((state) => state.tier);
  const refreshDate = useCreditsStore((state) => state.refreshDate);
  const weeklyLimit = useCreditsStore((state) =>
    state.tier === "infinite" || state.tier === "admin" ? undefined : state.weeklyLimit
  );
  const { topOffset } = useDebugBanner();

  const initials = user?.display_name
    ? user.display_name
        .split(" ")
        .map((n: string) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : (user?.username?.slice(0, 2).toUpperCase() ?? "?");

  return (
    <header
      className={`sticky ${topOffset} z-50 border-b border-border bg-surface px-4 py-3 md:px-6`}
    >
      <div className="flex items-center justify-between">
        {/* Left side */}
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={toggleSidebar} className="md:hidden">
            <Menu className="h-5 w-5" />
            <span className="sr-only">Toggle sidebar</span>
          </Button>

          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <span className="text-sm font-bold">FS</span>
            </div>
            <span className="hidden text-lg font-semibold text-foreground md:inline">
              Focus Squad
            </span>
          </Link>
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2 md:gap-4">
          <CreditBadge
            credits={credits}
            maxCredits={weeklyLimit}
            refreshDate={refreshDate}
            onClick={() => openModal("upgrade")}
            size="sm"
            className="hidden sm:flex"
          />

          <Button variant="ghost" size="icon" className="relative">
            <Bell className="h-5 w-5" />
            <span className="sr-only">Notifications</span>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full">
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-accent text-accent-foreground text-xs">
                    {initials}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="px-2 py-1.5">
                <p className="text-sm font-medium">{user?.display_name ?? user?.username}</p>
                <p className="text-xs text-muted-foreground">{user?.email}</p>
                <p className="mt-1 text-xs text-muted-foreground capitalize">{tier} tier</p>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/profile" className="flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Profile
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-destructive focus:text-destructive">
                <LogOut className="mr-2 h-4 w-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
