"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { getApplications } from "@/lib/api";
import { supabase } from "@/lib/supabase";
import { daysAgo } from "@/lib/utils";

const STATUS_COLUMNS = [
  { key: "processing", label: "Processing", color: "bg-blue-500" },
  { key: "applied", label: "Applied", color: "bg-green-500" },
  { key: "viewed", label: "Viewed", color: "bg-yellow-500" },
  { key: "interview", label: "Interview", color: "bg-purple-500" },
  { key: "offer", label: "Offer", color: "bg-emerald-500" },
  { key: "rejected", label: "Rejected", color: "bg-red-400" },
];

export default function DashboardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["applications"],
    queryFn: () => getApplications(),
  });

  // Supabase Realtime — live tracker updates
  useEffect(() => {
    const setupRealtime = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return;

      const channel = supabase
        .channel("tracker-updates")
        .on(
          "postgres_changes",
          {
            event: "INSERT",
            schema: "public",
            table: "tracker_events",
            filter: `user_id=eq.${session.user.id}`,
          },
          (payload) => {
            queryClient.invalidateQueries({ queryKey: ["applications"] });
            const evt = payload.new as { event_type: string; metadata?: { company?: string } };
            toast.success(`${evt.event_type} — ${evt.metadata?.company || "Application updated"}`);
          }
        )
        .subscribe();

      return () => {
        supabase.removeChannel(channel);
      };
    };
    setupRealtime();
  }, [queryClient]);

  const applications = data?.applications || [];

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-[var(--border)] px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <h1 className="text-xl font-bold">Job Tracker</h1>
          <div className="flex gap-3">
            <button
              onClick={() => router.push("/apply")}
              className="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)]"
            >
              + Apply
            </button>
            <button
              onClick={() => router.push("/prepare")}
              className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm"
            >
              Prepare
            </button>
            <button
              onClick={() => router.push("/profile")}
              className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm"
            >
              Profile
            </button>
          </div>
        </div>
      </header>

      {/* Board */}
      <div className="mx-auto max-w-7xl overflow-x-auto px-6 py-6">
        {isLoading ? (
          <div className="flex items-center justify-center py-20 text-[var(--muted-foreground)]">
            Loading applications...
          </div>
        ) : applications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <p className="text-lg text-[var(--muted-foreground)]">No applications yet</p>
            <button
              onClick={() => router.push("/apply")}
              className="mt-4 rounded-lg bg-[var(--primary)] px-6 py-3 font-medium text-[var(--primary-foreground)]"
            >
              Start your first application
            </button>
          </div>
        ) : (
          <div className="flex gap-4">
            {STATUS_COLUMNS.map((col) => {
              const colApps = applications.filter(
                (a: { status: string }) => a.status === col.key
              );
              return (
                <div key={col.key} className="w-72 shrink-0">
                  <div className="mb-3 flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${col.color}`} />
                    <span className="text-sm font-medium">{col.label}</span>
                    <span className="text-xs text-[var(--muted-foreground)]">
                      {colApps.length}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {colApps.map(
                      (app: {
                        id: string;
                        company_name: string;
                        role_title: string;
                        submitted_at: string;
                        jd_overlap_score: number | null;
                      }) => (
                        <div
                          key={app.id}
                          onClick={() => router.push(`/apply/review/${app.id}`)}
                          className="cursor-pointer rounded-lg border border-[var(--border)] bg-[var(--background)] p-3 hover:border-[var(--primary)] transition-colors"
                        >
                          <p className="font-medium text-sm">{app.company_name}</p>
                          <p className="text-xs text-[var(--muted-foreground)]">
                            {app.role_title}
                          </p>
                          <div className="mt-2 flex items-center justify-between">
                            <span className="text-xs text-[var(--muted-foreground)]">
                              {daysAgo(app.submitted_at)}
                            </span>
                            {app.jd_overlap_score != null && (
                              <span className="rounded bg-[var(--muted)] px-1.5 py-0.5 text-xs">
                                {Math.round(app.jd_overlap_score * 100)}% match
                              </span>
                            )}
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
