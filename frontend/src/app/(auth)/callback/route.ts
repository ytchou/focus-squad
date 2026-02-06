import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const redirectTo = requestUrl.searchParams.get("redirect") || "/dashboard";

  console.log("[Callback] Received request to /callback");
  console.log("[Callback] Code present:", !!code);
  console.log("[Callback] Redirect to:", redirectTo);

  if (code) {
    const supabase = await createClient();
    console.log("[Callback] Exchanging code for session...");

    const { data, error } = await supabase.auth.exchangeCodeForSession(code);

    if (error) {
      console.error("[Callback] Error exchanging code for session:", error);
      return NextResponse.redirect(new URL("/login?error=auth_failed", request.url));
    }

    console.log("[Callback] Session exchange successful:", !!data.session);
    console.log("[Callback] User:", data.user?.email);
  } else {
    console.warn("[Callback] No code found in URL");
  }

  // Redirect to the destination or dashboard
  console.log("[Callback] Redirecting to:", redirectTo);
  return NextResponse.redirect(new URL(redirectTo, request.url));
}
