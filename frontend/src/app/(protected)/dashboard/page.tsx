import { createClient } from "@/lib/supabase/server";
import { LogoutButton } from "@/components/auth/logout-button";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <div className="min-h-screen bg-[#FAF7F2]">
      <header className="border-b border-[#D4A574] bg-[#F5EFE6] px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <h1 className="text-xl font-semibold text-[#3D3D3D]">Focus Squad</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-[#8B7355]">{user?.email}</span>
            <LogoutButton />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="rounded-2xl bg-[#F5EFE6] p-8 shadow-lg">
          <h2 className="mb-4 text-2xl font-semibold text-[#3D3D3D]">Welcome to Focus Squad!</h2>
          <p className="text-[#8B7355]">
            Your dashboard is ready. This is where you&apos;ll find your upcoming sessions, stats,
            and more.
          </p>

          <div className="mt-8 grid gap-6 md:grid-cols-3">
            <div className="rounded-xl bg-white p-6 shadow-sm">
              <h3 className="text-lg font-medium text-[#3D3D3D]">Sessions</h3>
              <p className="mt-2 text-3xl font-bold text-[#8B7355]">0</p>
              <p className="mt-1 text-sm text-[#8B7355]">completed this week</p>
            </div>

            <div className="rounded-xl bg-white p-6 shadow-sm">
              <h3 className="text-lg font-medium text-[#3D3D3D]">Focus Time</h3>
              <p className="mt-2 text-3xl font-bold text-[#8B7355]">0 min</p>
              <p className="mt-1 text-sm text-[#8B7355]">total focus time</p>
            </div>

            <div className="rounded-xl bg-white p-6 shadow-sm">
              <h3 className="text-lg font-medium text-[#3D3D3D]">Credits</h3>
              <p className="mt-2 text-3xl font-bold text-[#8B7355]">2</p>
              <p className="mt-1 text-sm text-[#8B7355]">available this week</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
