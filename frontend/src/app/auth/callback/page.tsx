"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function AuthCallback() {
  const router = useRouter();

  useEffect(() => {
    supabase.auth.onAuthStateChange(async (event) => {
      if (event === "SIGNED_IN") {
        // Check if user has completed onboarding
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) {
          router.push("/login");
          return;
        }

        try {
          const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          const res = await fetch(`${API}/profile`, {
            headers: { Authorization: `Bearer ${session.access_token}` },
          });
          if (res.ok) {
            const profile = await res.json();
            if (profile.onboarded) {
              router.push("/dashboard");
            } else {
              router.push("/onboarding");
            }
          } else {
            router.push("/onboarding");
          }
        } catch {
          router.push("/dashboard");
        }
      }
    });
  }, [router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-[var(--muted-foreground)]">Signing you in...</p>
    </div>
  );
}
