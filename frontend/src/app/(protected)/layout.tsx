import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { AuthProvider } from "@/components/providers/auth-provider";

export default async function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  // AuthProvider handles client-side user/credits state initialization
  return <AuthProvider>{children}</AuthProvider>;
}
