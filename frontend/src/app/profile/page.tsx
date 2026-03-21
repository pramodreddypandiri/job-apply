"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { getProfile, getSkillGraph, analyseProfile } from "@/lib/api";
import { supabase } from "@/lib/supabase";

const CATEGORY_LABELS: Record<string, string> = {
  cs_fundamentals: "CS Fundamentals",
  system_design: "System Design",
  stack: "Tech Stack",
  behavioural: "Behavioural",
};

export default function ProfilePage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: profile, isLoading: profileLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: getProfile,
  });

  const { data: skillGraph } = useQuery({
    queryKey: ["skill-graph"],
    queryFn: getSkillGraph,
  });

  const analyseMutation = useMutation({
    mutationFn: analyseProfile,
    onSuccess: () => {
      toast.success("Profile analysis started — skills will update shortly");
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["skill-graph"] }), 10000);
    },
  });

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/onboarding");
  }

  if (profileLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-[var(--muted-foreground)]">
        Loading profile...
      </div>
    );
  }

  const skills = skillGraph?.skills || [];
  const grouped = skills.reduce(
    (acc: Record<string, typeof skills>, s: { category?: string }) => {
      const cat = s.category || "other";
      (acc[cat] ||= []).push(s);
      return acc;
    },
    {} as Record<string, typeof skills>
  );

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <button
            onClick={() => router.push("/dashboard")}
            className="mb-2 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
          >
            &larr; Back
          </button>
          <h1 className="text-2xl font-bold">Profile</h1>
        </div>
        <button
          onClick={handleSignOut}
          className="text-sm text-[var(--muted-foreground)] hover:text-[var(--destructive)]"
        >
          Sign out
        </button>
      </div>

      {/* Profile summary */}
      {profile && (
        <div className="mb-8 rounded-lg border border-[var(--border)] p-6">
          <h2 className="font-semibold">{profile.full_name || profile.email}</h2>
          {profile.target_roles && (
            <p className="mt-1 text-sm text-[var(--muted-foreground)]">
              Targeting: {profile.target_roles.join(", ")}
            </p>
          )}
          {profile.skill_graph_summary && (
            <div className="mt-4 flex gap-6 text-sm">
              <div>
                <span className="text-xl font-bold">{profile.skill_graph_summary.total_skills}</span>
                <span className="ml-1 text-[var(--muted-foreground)]">skills</span>
              </div>
              <div>
                <span className="text-xl font-bold">{profile.skill_graph_summary.avg_depth}</span>
                <span className="ml-1 text-[var(--muted-foreground)]">avg depth</span>
              </div>
            </div>
          )}
          <button
            onClick={() => analyseMutation.mutate()}
            disabled={analyseMutation.isPending}
            className="mt-4 rounded-lg border border-[var(--border)] px-4 py-2 text-sm hover:bg-[var(--muted)] disabled:opacity-50"
          >
            {analyseMutation.isPending ? "Analysing..." : "Re-analyse profile"}
          </button>
        </div>
      )}

      {/* Skill graph */}
      <h2 className="mb-4 text-lg font-semibold">Skill Graph</h2>
      {Object.entries(grouped).length === 0 ? (
        <p className="text-sm text-[var(--muted-foreground)]">
          No skills yet. Complete onboarding and run profile analysis.
        </p>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([category, catSkills]) => (
            <div key={category}>
              <h3 className="mb-2 text-sm font-medium text-[var(--muted-foreground)]">
                {CATEGORY_LABELS[category] || category}
              </h3>
              <div className="grid gap-2 sm:grid-cols-2">
                {(catSkills as { skill_name: string; depth: number; source: string[]; interview_defensible: boolean }[]).map(
                  (skill) => (
                    <div
                      key={skill.skill_name}
                      className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2"
                    >
                      <div>
                        <p className="text-sm font-medium">{skill.skill_name}</p>
                        <div className="flex gap-1">
                          {skill.source?.map((s) => (
                            <span
                              key={s}
                              className="rounded bg-[var(--muted)] px-1 py-0.5 text-[10px]"
                            >
                              {s}
                            </span>
                          ))}
                          {skill.interview_defensible && (
                            <span className="rounded bg-green-100 px-1 py-0.5 text-[10px] text-green-700 dark:bg-green-900/30 dark:text-green-300">
                              defensible
                            </span>
                          )}
                        </div>
                      </div>
                      {/* Depth bar */}
                      <div className="flex gap-0.5">
                        {[1, 2, 3, 4, 5].map((d) => (
                          <div
                            key={d}
                            className={`h-4 w-1.5 rounded-sm ${
                              d <= skill.depth
                                ? "bg-[var(--primary)]"
                                : "bg-[var(--muted)]"
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  )
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Gmail connection */}
      <div className="mt-12 rounded-lg border border-[var(--border)] p-6">
        <h2 className="font-semibold">Integrations</h2>
        <div className="mt-4 space-y-3">
          <a
            href="http://localhost:8000/auth/gmail/connect"
            className="block rounded-lg border border-[var(--border)] px-4 py-3 text-sm hover:bg-[var(--muted)]"
          >
            Connect Gmail &rarr;
          </a>
        </div>
      </div>
    </div>
  );
}
