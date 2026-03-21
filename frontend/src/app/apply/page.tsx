"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { checkURL, startApplication } from "@/lib/api";

export default function ApplyPage() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [instructions, setInstructions] = useState("");
  const [checking, setChecking] = useState(false);
  const [starting, setStarting] = useState(false);
  const [duplicate, setDuplicate] = useState<{
    status: string;
    application?: { company_name: string; status: string };
    message?: string;
  } | null>(null);

  async function handleCheckURL() {
    if (!url.trim()) return;
    setChecking(true);
    setDuplicate(null);
    try {
      const result = await checkURL(url);
      if (result.status === "duplicate") {
        setDuplicate(result);
      }
    } catch (err) {
      console.error("Check URL error:", err);
    } finally {
      setChecking(false);
    }
  }

  async function handleStart() {
    if (!url.trim()) return;
    setStarting(true);
    try {
      const result = await startApplication(url, instructions || undefined);
      toast.success("Application pipeline started");
      router.push(`/apply/review/${result.application_id}`);
    } catch (err) {
      toast.error("Failed to start application");
      console.error(err);
    } finally {
      setStarting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <button
        onClick={() => router.push("/dashboard")}
        className="mb-6 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
      >
        &larr; Back to dashboard
      </button>

      <h1 className="text-2xl font-bold">Apply to a role</h1>
      <p className="mt-1 text-[var(--muted-foreground)]">
        Paste a job URL and we&apos;ll handle the rest.
      </p>

      <div className="mt-8 space-y-6">
        {/* URL Input */}
        <div>
          <label className="block text-sm font-medium">Job URL</label>
          <input
            type="url"
            placeholder="https://boards.greenhouse.io/company/jobs/123456"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onBlur={handleCheckURL}
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2"
          />
          {checking && (
            <p className="mt-1 text-xs text-[var(--muted-foreground)]">Checking for duplicates...</p>
          )}
        </div>

        {/* Duplicate Alert */}
        {duplicate && (
          <div className="rounded-lg border border-[var(--warning)] bg-yellow-50 p-4 dark:bg-yellow-950/20">
            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Duplicate detected
            </p>
            <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
              {duplicate.message}
            </p>
          </div>
        )}

        {/* Instructions */}
        {!duplicate && url && (
          <>
            <div>
              <label className="block text-sm font-medium">
                Instructions <span className="text-[var(--muted-foreground)]">(optional)</span>
              </label>
              <textarea
                placeholder="Emphasise distributed systems work, mention the Kafka project..."
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2"
              />
            </div>

            <button
              onClick={handleStart}
              disabled={starting}
              className="w-full rounded-lg bg-[var(--primary)] px-4 py-3 font-medium text-[var(--primary-foreground)] hover:opacity-90 transition-opacity disabled:opacity-50"
            >
              {starting ? "Starting pipeline..." : "Start applying"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
