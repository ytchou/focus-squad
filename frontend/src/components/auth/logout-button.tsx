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
      className="rounded-full border border-[#D4A574] px-4 py-1.5 text-sm text-[#8B7355] transition-colors hover:bg-[#D4A574]/10"
    >
      Sign out
    </button>
  );
}
