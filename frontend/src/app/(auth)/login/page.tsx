import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { LoginButton } from "@/components/auth/login-button";

interface LoginPageProps {
  searchParams: Promise<{ redirect?: string; error?: string }>;
}

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const params = await searchParams;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user) {
    redirect("/dashboard");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#FAF7F2]">
      <div className="w-full max-w-md rounded-2xl bg-[#F5EFE6] p-8 shadow-lg">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-semibold text-[#3D3D3D]">Welcome to Focus Squad</h1>
          <p className="mt-2 text-[#8B7355]">Body-doubling for focused study sessions</p>
        </div>

        {params.error && (
          <div className="mb-4 rounded-lg bg-[#B85C5C]/10 p-3 text-[#B85C5C]">
            Authentication failed. Please try again.
          </div>
        )}

        <LoginButton redirectTo={params.redirect} />

        <p className="mt-6 text-center text-sm text-[#8B7355]">
          By signing in, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}
