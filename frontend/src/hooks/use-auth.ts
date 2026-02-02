"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useUserStore, type UserProfile } from "@/stores/user-store";
import { api, ApiError } from "@/lib/api/client";

export function useAuth() {
  const router = useRouter();
  const { user, isLoading, error, setUser, setLoading, setError, clearUser } = useUserStore();

  useEffect(() => {
    const supabase = createClient();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === "SIGNED_IN" && session) {
        setLoading(true);
        try {
          const profile = await api.get<UserProfile>("/users/me");
          setUser(profile);
        } catch (err) {
          if (err instanceof ApiError) {
            setError(err.message);
          } else {
            setError("Failed to load profile");
          }
        }
      } else if (event === "SIGNED_OUT") {
        clearUser();
      }
    });

    return () => subscription.unsubscribe();
  }, [setUser, setLoading, setError, clearUser]);

  const signOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    clearUser();
    router.push("/login");
  };

  const refreshProfile = async () => {
    setLoading(true);
    try {
      const profile = await api.get<UserProfile>("/users/me");
      setUser(profile);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Failed to refresh profile");
      }
    }
  };

  return {
    user,
    isLoading,
    error,
    isAuthenticated: !!user,
    signOut,
    refreshProfile,
  };
}
