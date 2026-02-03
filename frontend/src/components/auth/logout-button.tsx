"use client";

import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useUserStore } from "@/stores/user-store";

export function LogoutButton() {
  const router = useRouter();
  const clearUser = useUserStore((state) => state.clearUser);

  const handleLogout = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    clearUser();
    router.push("/login");
  };

  return (
    <button
      onClick={handleLogout}
      className="rounded-full border border-accent px-4 py-1.5 text-sm text-primary transition-colors hover:bg-accent/10"
    >
      Sign out
    </button>
  );
}
