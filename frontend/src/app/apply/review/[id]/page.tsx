"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  getApplication,
  getApplicationStatus,
  getResumeDiff,
  approveApplication,
  discardApplication,
} from "@/lib/api";

const STEP_LABELS: Record<string, string> = {
  parsing_jd: "Parsing job description...",
  tailoring: "Tailoring your resume...",
  review_pending: "Ready for your review",
  filling_form: "Filling application form...",
  submitted: "Submitted!",
  needs_action: "Needs your attention",
};

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: statusData } = useQuery({
    queryKey: ["application-status", id],
    queryFn: () => getApplicationStatus(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "processing" ? 3000 : false;
    },
  });

  const { data: appData } = useQuery({
    queryKey: ["application", id],
    queryFn: () => getApplication(id),
    enabled: statusData?.status === "review_pending" || statusData?.status === "applied",
  });

  const { data: diffData } = useQuery({
    queryKey: ["resume-diff", id],
    queryFn: () => getResumeDiff(id),
    enabled: statusData?.status === "review_pending",
  });

  const approveMutation = useMutation({
    mutationFn: () => approveApplication(id),
    onSuccess: () => {
      toast.success("Resume approved — form fill started");
      queryClient.invalidateQueries({ queryKey: ["application-status", id] });
    },
  });

  const discardMutation = useMutation({
    mutationFn: () => discardApplication(id),
    onSuccess: () => {
      toast.info("Application discarded");
      router.push("/dashboard");
    },
  });

  const status = statusData?.status || "processing";
  const step = statusData?.step || "parsing_jd";
  const progress = statusData?.progress || 0;

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <button
        onClick={() => router.push("/dashboard")}
        className="mb-6 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
      >
        &larr; Back to dashboard
      </button>

      {/* Application header */}
      {appData?.application && (
        <div className="mb-8">
          <h1 className="text-2xl font-bold">{appData.application.company_name}</h1>
          <p className="text-[var(--muted-foreground)]">{appData.application.role_title}</p>
        </div>
      )}

      {/* Processing state */}
      {status === "processing" && (
        <div className="rounded-lg border border-[var(--border)] p-8 text-center">
          <div className="mx-auto mb-4 h-2 w-64 overflow-hidden rounded-full bg-[var(--muted)]">
            <div
              className="h-full rounded-full bg-[var(--primary)] transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="font-medium">{STEP_LABELS[step] || "Processing..."}</p>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            This usually takes 30–60 seconds
          </p>
        </div>
      )}

      {/* Review state */}
      {status === "review_pending" && diffData && (
        <div className="space-y-6">
          {/* Stats */}
          <div className="flex gap-4">
            <div className="rounded-lg border border-[var(--border)] px-4 py-3">
              <p className="text-2xl font-bold">{diffData.pct_changed}%</p>
              <p className="text-xs text-[var(--muted-foreground)]">changed from master</p>
            </div>
            <div className="rounded-lg border border-[var(--border)] px-4 py-3">
              <p className="text-2xl font-bold">{Math.round(diffData.jd_overlap_score * 100)}%</p>
              <p className="text-xs text-[var(--muted-foreground)]">JD overlap</p>
            </div>
            {diffData.skills_added.length > 0 && (
              <div className="rounded-lg border border-[var(--border)] px-4 py-3">
                <p className="text-2xl font-bold">{diffData.skills_added.length}</p>
                <p className="text-xs text-[var(--muted-foreground)]">skills elevated</p>
              </div>
            )}
          </div>

          {/* Changes */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Changes</h2>
            {diffData.sections.map((section: { section: string; items: { type: string; original: string | null; new: string; reason: string }[] }) => (
              <div key={section.section} className="rounded-lg border border-[var(--border)] p-4">
                <h3 className="mb-2 font-medium capitalize">{section.section}</h3>
                {section.items.map((item: { type: string; original: string | null; new: string; reason: string }, i: number) => (
                  <div key={i} className="mb-3 last:mb-0">
                    <span
                      className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${
                        item.type === "elevated"
                          ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
                          : item.type === "reframed"
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300"
                            : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                      }`}
                    >
                      {item.type}
                    </span>
                    {item.original && (
                      <p className="mt-1 text-sm text-[var(--muted-foreground)] line-through">
                        {item.original}
                      </p>
                    )}
                    <p className="text-sm">{item.new}</p>
                    <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">
                      {item.reason}
                    </p>
                  </div>
                ))}
              </div>
            ))}
          </div>

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending}
              className="flex-1 rounded-lg bg-[var(--primary)] px-4 py-3 font-medium text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
            >
              {approveMutation.isPending ? "Approving..." : "Approve & Submit"}
            </button>
            <button
              onClick={() => discardMutation.mutate()}
              disabled={discardMutation.isPending}
              className="rounded-lg border border-[var(--border)] px-4 py-3 text-sm hover:bg-[var(--muted)]"
            >
              Discard
            </button>
          </div>
        </div>
      )}

      {/* Applied state */}
      {status === "applied" && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-8 text-center dark:border-green-800 dark:bg-green-950/20">
          <p className="text-lg font-medium text-green-800 dark:text-green-200">
            Application submitted!
          </p>
          <p className="mt-1 text-sm text-green-600 dark:text-green-400">
            We&apos;ll monitor your inbox for updates.
          </p>
          <button
            onClick={() => router.push("/dashboard")}
            className="mt-4 rounded-lg bg-[var(--primary)] px-6 py-2 text-sm font-medium text-[var(--primary-foreground)]"
          >
            Back to tracker
          </button>
        </div>
      )}

      {/* Needs action */}
      {status === "needs_action" && (
        <div className="rounded-lg border border-[var(--warning)] bg-yellow-50 p-8 text-center dark:bg-yellow-950/20">
          <p className="text-lg font-medium">Agent needs your help</p>
          <p className="mt-1 text-sm text-[var(--muted-foreground)]">
            Something went wrong during the application process. Check the details and try again.
          </p>
        </div>
      )}
    </div>
  );
}
