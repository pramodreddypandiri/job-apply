"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";

const FEATURES = [
  {
    title: "Paste a Job URL",
    desc: "Drop any job listing URL and we parse the JD, detect the ATS, and extract what matters.",
    icon: "🔗",
  },
  {
    title: "AI-Tailored Resume",
    desc: "Your master resume is automatically rewritten to match each role — with an authenticity guard.",
    icon: "📄",
  },
  {
    title: "One-Click Apply",
    desc: "Auto-fill application forms on Greenhouse, Lever, Workday, and more via browser automation.",
    icon: "🚀",
  },
  {
    title: "Smart Tracker",
    desc: "Track every application. Gmail integration detects replies, interviews, and rejections automatically.",
    icon: "📊",
  },
  {
    title: "Interview Prep",
    desc: "When an interview invite lands, a custom prep plan with STAR stories is ready in minutes.",
    icon: "🎯",
  },
  {
    title: "Skill Graph",
    desc: "A living map of your skills — built from your resume, GitHub, and portfolio — that grows over time.",
    icon: "🧠",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        router.push("/dashboard");
      } else {
        setChecking(false);
      }
    });
  }, [router]);

  if (checking) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-pulse text-lg text-[var(--muted-foreground)]">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Nav */}
      <nav className="border-b border-[var(--border)] px-6 py-4">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <span className="text-xl font-bold">Job Agent</span>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium hover:bg-[var(--muted)] transition-colors"
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] hover:opacity-90 transition-opacity"
            >
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 py-24 text-center">
        <h1 className="text-5xl font-bold leading-tight tracking-tight sm:text-6xl">
          Stop applying manually.
          <br />
          <span className="text-[var(--primary)]">Let AI handle it.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-[var(--muted-foreground)]">
          Paste a job URL. Get a tailored resume in seconds. Auto-submit the application.
          Track everything from one dashboard.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link
            href="/signup"
            className="rounded-lg bg-[var(--primary)] px-8 py-3.5 text-base font-medium text-[var(--primary-foreground)] hover:opacity-90 transition-opacity"
          >
            Get started — it&apos;s free
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-[var(--border)] px-8 py-3.5 text-base font-medium hover:bg-[var(--muted)] transition-colors"
          >
            Log in
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-[var(--border)] bg-[var(--muted)] px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-center text-3xl font-bold">Everything you need to land your next role</h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-[var(--muted-foreground)]">
            From parsing job descriptions to prepping for interviews — fully automated.
          </p>
          <div className="mt-14 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-6"
              >
                <div className="text-3xl">{f.icon}</div>
                <h3 className="mt-3 text-lg font-semibold">{f.title}</h3>
                <p className="mt-2 text-sm text-[var(--muted-foreground)] leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-center text-3xl font-bold">How it works</h2>
          <div className="mt-14 space-y-12">
            {[
              { step: "1", title: "Build your master resume", desc: "Upload your resume or fill it in manually. Connect GitHub and your portfolio for a richer skill profile." },
              { step: "2", title: "Paste a job URL", desc: "We parse the job description, detect the ATS, and identify exactly what the role needs." },
              { step: "3", title: "Review your tailored resume", desc: "See a side-by-side diff of what changed. Approve, edit, or discard — you're always in control." },
              { step: "4", title: "Auto-submit and track", desc: "We fill out the application form and submit. Track status, get notified on replies, and prep for interviews." },
            ].map((s) => (
              <div key={s.step} className="flex gap-6">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--primary)] text-lg font-bold text-[var(--primary-foreground)]">
                  {s.step}
                </div>
                <div>
                  <h3 className="text-lg font-semibold">{s.title}</h3>
                  <p className="mt-1 text-[var(--muted-foreground)]">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-[var(--border)] bg-[var(--muted)] px-6 py-20 text-center">
        <h2 className="text-3xl font-bold">Ready to automate your job search?</h2>
        <p className="mt-3 text-[var(--muted-foreground)]">
          Sign up in 30 seconds with your Google account.
        </p>
        <Link
          href="/signup"
          className="mt-8 inline-block rounded-lg bg-[var(--primary)] px-8 py-3.5 text-base font-medium text-[var(--primary-foreground)] hover:opacity-90 transition-opacity"
        >
          Get started
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] px-6 py-8">
        <div className="mx-auto max-w-6xl text-center text-sm text-[var(--muted-foreground)]">
          Job Agent — AI-powered job applications
        </div>
      </footer>
    </div>
  );
}
