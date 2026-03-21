"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { onboard } from "@/lib/api";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<"auth" | "profile">("auth");
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    target_roles: "",
    target_locations: "",
    seniority_floor: "senior",
    github_username: "",
    linkedin_url: "",
    portfolio_url: "",
  });
  const [resumeFile, setResumeFile] = useState<File | null>(null);

  async function handleGoogleLogin() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) console.error("Login error:", error);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("target_roles", form.target_roles);
      formData.append("target_locations", form.target_locations);
      formData.append("seniority_floor", form.seniority_floor);
      formData.append("github_username", form.github_username);
      formData.append("linkedin_url", form.linkedin_url);
      formData.append("portfolio_url", form.portfolio_url);
      if (resumeFile) formData.append("resume_pdf", resumeFile);

      await onboard(formData);
      router.push("/dashboard");
    } catch (err) {
      console.error("Onboarding error:", err);
    } finally {
      setLoading(false);
    }
  }

  // Check if already logged in
  supabase.auth.getSession().then(({ data: { session } }) => {
    if (session) setStep("profile");
  });

  if (step === "auth") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="w-full max-w-md space-y-8 p-8">
          <div className="text-center">
            <h1 className="text-3xl font-bold">Job Agent</h1>
            <p className="mt-2 text-[var(--muted-foreground)]">
              AI-powered job applications
            </p>
          </div>
          <button
            onClick={handleGoogleLogin}
            className="w-full rounded-lg bg-[var(--primary)] px-4 py-3 font-medium text-[var(--primary-foreground)] hover:opacity-90 transition-opacity"
          >
            Sign in with Google
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-2xl font-bold">Set up your profile</h1>
      <p className="mt-1 text-[var(--muted-foreground)]">
        We&apos;ll use this to tailor your applications.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        <div>
          <label className="block text-sm font-medium">Target roles</label>
          <input
            type="text"
            placeholder="Senior Backend Engineer, Staff Engineer"
            value={form.target_roles}
            onChange={(e) => setForm({ ...form, target_roles: e.target.value })}
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2"
            required
          />
          <p className="mt-1 text-xs text-[var(--muted-foreground)]">Comma-separated</p>
        </div>

        <div>
          <label className="block text-sm font-medium">Target locations</label>
          <input
            type="text"
            placeholder="Remote, London, Berlin"
            value={form.target_locations}
            onChange={(e) => setForm({ ...form, target_locations: e.target.value })}
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium">Seniority floor</label>
          <select
            value={form.seniority_floor}
            onChange={(e) => setForm({ ...form, seniority_floor: e.target.value })}
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2"
          >
            <option value="any">Any</option>
            <option value="senior">Senior</option>
            <option value="staff">Staff</option>
            <option value="principal">Principal</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium">Resume PDF</label>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
            className="mt-1 w-full text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium">GitHub username</label>
          <input
            type="text"
            placeholder="octocat"
            value={form.github_username}
            onChange={(e) => setForm({ ...form, github_username: e.target.value })}
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium">LinkedIn URL</label>
          <input
            type="url"
            placeholder="https://linkedin.com/in/..."
            value={form.linkedin_url}
            onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })}
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium">Portfolio URL</label>
          <input
            type="url"
            placeholder="https://yoursite.com"
            value={form.portfolio_url}
            onChange={(e) => setForm({ ...form, portfolio_url: e.target.value })}
            className="mt-1 w-full rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-[var(--primary)] px-4 py-3 font-medium text-[var(--primary-foreground)] hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loading ? "Setting up..." : "Complete setup"}
        </button>
      </form>
    </div>
  );
}
