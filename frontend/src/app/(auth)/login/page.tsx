import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
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

  const t = await getTranslations("auth");

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="w-full max-w-md rounded-2xl bg-card p-8 shadow-lg">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-semibold text-foreground">{t("signInTitle")}</h1>
          <p className="mt-2 text-primary">{t("signInSubtitle")}</p>
        </div>

        {params.error && (
          <div className="mb-4 rounded-lg bg-destructive/10 p-3 text-destructive">
            {t("errorCallback")}
          </div>
        )}

        <LoginButton redirectTo={params.redirect} />

        <p className="mt-6 text-center text-sm text-primary">{t("termsAgreement")}</p>
      </div>
    </div>
  );
}
