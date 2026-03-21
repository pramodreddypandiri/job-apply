"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { getPrepToday, getPrepAnswer, ratePrepSession } from "@/lib/api";

type Rating = "got_it" | "unsure" | "missed";

export default function PreparePage() {
  const router = useRouter();
  const [currentQ, setCurrentQ] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  const [ratings, setRatings] = useState<Record<string, Rating>>({});
  const [submitted, setSubmitted] = useState(false);

  const { data: session, isLoading } = useQuery({
    queryKey: ["prepare-today"],
    queryFn: getPrepToday,
    staleTime: 1000 * 60 * 60,
  });

  const answerQuery = useQuery({
    queryKey: ["prep-answer", session?.questions?.[currentQ]?.id],
    queryFn: () => getPrepAnswer(session.questions[currentQ].id),
    enabled: showAnswer && !!session?.questions?.[currentQ]?.id,
  });

  const rateMutation = useMutation({
    mutationFn: () =>
      ratePrepSession(
        session.topic,
        Object.entries(ratings).map(([question_id, rating]) => ({
          question_id,
          rating,
        }))
      ),
    onSuccess: (data) => {
      setSubmitted(true);
      toast.success(data.message);
    },
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-[var(--muted-foreground)]">
        Loading today&apos;s session...
      </div>
    );
  }

  if (!session) return null;

  const questions = session.questions || [];
  const question = questions[currentQ];
  const allRated = questions.every((q: { id: string }) => ratings[q.id]);

  if (submitted) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 text-center">
        <h1 className="text-2xl font-bold">Session complete</h1>
        <p className="mt-2 text-[var(--muted-foreground)]">
          {rateMutation.data?.message}
        </p>
        <div className="mt-6 flex justify-center gap-4">
          <button
            onClick={() => router.push("/dashboard")}
            className="rounded-lg border border-[var(--border)] px-6 py-2"
          >
            Dashboard
          </button>
          <button
            onClick={() => router.push("/prepare")}
            className="rounded-lg bg-[var(--primary)] px-6 py-2 text-[var(--primary-foreground)]"
          >
            Topics overview
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <button
        onClick={() => router.push("/dashboard")}
        className="mb-6 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
      >
        &larr; Back
      </button>

      {/* Header */}
      <div className="mb-8">
        <span className="rounded bg-[var(--muted)] px-2 py-0.5 text-xs font-medium uppercase">
          {session.category}
        </span>
        <h1 className="mt-2 text-2xl font-bold">{session.topic}</h1>
        <p className="text-sm text-[var(--muted-foreground)]">
          Current depth: {session.current_depth}/5 &middot; Question {currentQ + 1}/{questions.length}
        </p>
      </div>

      {/* Concept brief */}
      {session.brief && (
        <details className="mb-6 rounded-lg border border-[var(--border)] p-4">
          <summary className="cursor-pointer text-sm font-medium">
            Concept brief (try to answer first)
          </summary>
          <p className="mt-2 text-sm text-[var(--muted-foreground)]">{session.brief}</p>
        </details>
      )}

      {/* Question */}
      {question && (
        <div className="space-y-4">
          <div className="rounded-lg border border-[var(--border)] p-6">
            <p className="text-lg font-medium">{question.question}</p>
          </div>

          {/* Answer reveal */}
          {!showAnswer ? (
            <button
              onClick={() => setShowAnswer(true)}
              className="w-full rounded-lg border border-[var(--border)] px-4 py-3 text-sm hover:bg-[var(--muted)]"
            >
              See answer
            </button>
          ) : (
            <div className="rounded-lg border border-[var(--border)] bg-[var(--muted)] p-4">
              <p className="text-sm whitespace-pre-wrap">
                {answerQuery.isLoading
                  ? "Loading answer..."
                  : answerQuery.data?.answer || "Answer not available"}
              </p>
            </div>
          )}

          {/* Rating buttons */}
          {showAnswer && (
            <div className="flex gap-3">
              {(["got_it", "unsure", "missed"] as Rating[]).map((r) => (
                <button
                  key={r}
                  onClick={() => {
                    setRatings({ ...ratings, [question.id]: r });
                    setShowAnswer(false);
                    if (currentQ < questions.length - 1) {
                      setCurrentQ(currentQ + 1);
                    }
                  }}
                  className={`flex-1 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                    ratings[question.id] === r
                      ? "border-[var(--primary)] bg-[var(--primary)] text-[var(--primary-foreground)]"
                      : "border-[var(--border)] hover:bg-[var(--muted)]"
                  }`}
                >
                  {r === "got_it" ? "Got it" : r === "unsure" ? "Unsure" : "Missed"}
                </button>
              ))}
            </div>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between pt-4">
            <button
              onClick={() => {
                setCurrentQ(Math.max(0, currentQ - 1));
                setShowAnswer(false);
              }}
              disabled={currentQ === 0}
              className="text-sm text-[var(--muted-foreground)] disabled:opacity-30"
            >
              Previous
            </button>

            {allRated ? (
              <button
                onClick={() => rateMutation.mutate()}
                disabled={rateMutation.isPending}
                className="rounded-lg bg-[var(--primary)] px-6 py-2 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-50"
              >
                {rateMutation.isPending ? "Submitting..." : "Finish session"}
              </button>
            ) : (
              <button
                onClick={() => {
                  setCurrentQ(Math.min(questions.length - 1, currentQ + 1));
                  setShowAnswer(false);
                }}
                disabled={currentQ === questions.length - 1}
                className="text-sm text-[var(--muted-foreground)] disabled:opacity-30"
              >
                Next
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
