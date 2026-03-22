import { supabase } from "./supabase";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch(path: string, options?: RequestInit) {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    throw new Error("Not authenticated");
  }

  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(error.error?.message || res.statusText);
  }

  return res.json();
}

// ── Profile ───────────────────────────────────────────
export const getProfile = () => apiFetch("/profile");
export const getSkillGraph = () => apiFetch("/profile/skill-graph");
export const analyseProfile = () => apiFetch("/profile/analyse", { method: "POST" });

export async function onboard(formData: FormData) {
  const { data: { session } } = await supabase.auth.getSession();
  const res = await fetch(`${API}/profile/onboard`, {
    method: "POST",
    headers: { Authorization: `Bearer ${session?.access_token}` },
    body: formData,
  });
  if (!res.ok) throw new Error("Onboarding failed");
  return res.json();
}

// ── Master Resume ────────────────────────────────────
export const getResume = () => apiFetch("/resume");

export const saveResume = (data: Record<string, unknown>) =>
  apiFetch("/resume", {
    method: "PUT",
    body: JSON.stringify(data),
  });

export async function uploadResumePDF(file: File) {
  const { data: { session } } = await supabase.auth.getSession();
  const formData = new FormData();
  formData.append("resume_pdf", file);
  const res = await fetch(`${API}/resume/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${session?.access_token}` },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// ── Applications ──────────────────────────────────────
export const checkURL = (url: string) =>
  apiFetch("/applications/check", {
    method: "POST",
    body: JSON.stringify({ url }),
  });

export const startApplication = (url: string, instructions?: string, referral_context?: string) =>
  apiFetch("/applications/start", {
    method: "POST",
    body: JSON.stringify({ url, instructions, referral_context }),
  });

export const getApplications = (status?: string) =>
  apiFetch(`/applications${status ? `?status=${status}` : ""}`);

export const getApplication = (id: string) => apiFetch(`/applications/${id}`);

export const getApplicationStatus = (id: string) => apiFetch(`/applications/${id}/status`);

export const approveApplication = (id: string, resumeText?: string, coverLetterText?: string) =>
  apiFetch(`/applications/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ resume_text: resumeText, cover_letter_text: coverLetterText }),
  });

export const discardApplication = (id: string) =>
  apiFetch(`/applications/${id}/discard`, { method: "POST" });

export const getResumeDiff = (id: string) => apiFetch(`/applications/${id}/resume/diff`);

// ── Interview Prep ────────────────────────────────────
export const getInterviewPrep = (applicationId: string) =>
  apiFetch(`/applications/${applicationId}/prep`);

// ── Prepare Page ──────────────────────────────────────
export const getPrepToday = () => apiFetch("/prepare/today");

export const getPrepAnswer = (questionId: string) =>
  apiFetch(`/prepare/today/answer/${questionId}`);

export const ratePrepSession = (topic: string, ratings: { question_id: string; rating: string }[]) =>
  apiFetch("/prepare/today/rate", {
    method: "POST",
    body: JSON.stringify({ topic, ratings }),
  });

export const getPrepTopics = () => apiFetch("/prepare/topics");

// ── Tasks ─────────────────────────────────────────────
export const getTaskStatus = (taskId: string) => apiFetch(`/tasks/${taskId}`);
