"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { getInterviewPrep, getApplication } from "@/lib/api";

export default function InterviewPrepPage() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const router = useRouter();

  const { data: appData } = useQuery({
    queryKey: ["application", applicationId],
    queryFn: () => getApplication(applicationId),
  });

  const { data: prep, isLoading } = useQuery({
    queryKey: ["interview-prep", applicationId],
    queryFn: () => getInterviewPrep(applicationId),
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-[var(--muted-foreground)]">
        Loading prep plan...
      </div>
    );
  }

  const app = appData?.application;

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <button
        onClick={() => router.push("/dashboard")}
        className="mb-6 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
      >
        &larr; Back to dashboard
      </button>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold">Interview Prep</h1>
        {app && (
          <p className="text-[var(--muted-foreground)]">
            {app.company_name} &middot; {app.role_title}
          </p>
        )}
        {prep?.interview_type && (
          <div className="mt-2 flex gap-2">
            {prep.interview_type.map((t: string) => (
              <span
                key={t}
                className="rounded bg-[var(--muted)] px-2 py-0.5 text-xs font-medium"
              >
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {!prep ? (
        <p className="text-[var(--muted-foreground)]">
          No prep plan available yet. It will be generated when an interview invite is detected.
        </p>
      ) : (
        <div className="space-y-8">
          {/* Process summary */}
          {prep.process_summary && (
            <section>
              <h2 className="text-lg font-semibold">What to expect</h2>
              <p className="mt-2 text-sm">{prep.process_summary}</p>
            </section>
          )}

          {/* Day-by-day plan */}
          {prep.prep_plan?.days && (
            <section>
              <h2 className="text-lg font-semibold">Day-by-day plan</h2>
              <div className="mt-3 space-y-3">
                {prep.prep_plan.days.map(
                  (day: { day: number; focus: string; tasks: string[]; time_estimate_mins?: number }) => (
                    <details
                      key={day.day}
                      className="rounded-lg border border-[var(--border)] p-4"
                    >
                      <summary className="cursor-pointer font-medium">
                        Day {day.day}: {day.focus}
                        {day.time_estimate_mins && (
                          <span className="ml-2 text-xs text-[var(--muted-foreground)]">
                            ~{day.time_estimate_mins}min
                          </span>
                        )}
                      </summary>
                      <ul className="mt-2 space-y-1">
                        {day.tasks.map((task, i) => (
                          <li key={i} className="text-sm text-[var(--muted-foreground)]">
                            &bull; {task}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )
                )}
              </div>
            </section>
          )}

          {/* STAR stories */}
          {prep.star_stories?.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold">STAR Stories</h2>
              <div className="mt-3 space-y-3">
                {prep.star_stories.map(
                  (
                    story: {
                      theme: string;
                      project: string;
                      situation: string;
                      task: string;
                      action: string;
                      result: string;
                    },
                    i: number
                  ) => (
                    <details
                      key={i}
                      className="rounded-lg border border-[var(--border)] p-4"
                    >
                      <summary className="cursor-pointer font-medium">
                        {story.theme} — {story.project}
                      </summary>
                      <div className="mt-2 space-y-1 text-sm">
                        <p><strong>Situation:</strong> {story.situation}</p>
                        <p><strong>Task:</strong> {story.task}</p>
                        <p><strong>Action:</strong> {story.action}</p>
                        <p><strong>Result:</strong> {story.result}</p>
                      </div>
                    </details>
                  )
                )}
              </div>
            </section>
          )}

          {/* Claims to defend */}
          {prep.claims_to_defend?.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold">Claims to defend</h2>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                Bullets from your tailored resume — be ready to explain these.
              </p>
              <ul className="mt-3 space-y-2">
                {prep.claims_to_defend.map((claim: string, i: number) => (
                  <li
                    key={i}
                    className="rounded border border-[var(--border)] px-3 py-2 text-sm"
                  >
                    {claim}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Gap topics */}
          {prep.gap_topics?.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold">Gap topics</h2>
              <p className="mt-1 text-xs text-[var(--muted-foreground)]">
                Topics in the interview reports that aren&apos;t in your skill graph yet.
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {prep.gap_topics.map((topic: string) => (
                  <span
                    key={topic}
                    className="rounded bg-red-100 px-2 py-0.5 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
