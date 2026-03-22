"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { getResume, saveResume, uploadResumePDF } from "@/lib/api";
import { supabase } from "@/lib/supabase";

/* ── tiny helpers ─────────────────────────────────────── */
function Section({ title, children, onAdd }: { title: string; children: React.ReactNode; onAdd?: () => void }) {
  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">{title}</h2>
        {onAdd && (
          <button onClick={onAdd} className="text-sm text-[var(--primary)] hover:underline">
            + Add
          </button>
        )}
      </div>
      {children}
    </section>
  );
}

function Field({ label, value, onChange, placeholder, multiline }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; multiline?: boolean;
}) {
  const cls = "w-full rounded-md border border-[var(--border)] bg-[var(--muted)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none";
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">{label}</span>
      {multiline ? (
        <textarea value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} rows={3} className={cls} />
      ) : (
        <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={cls} />
      )}
    </label>
  );
}

function BulletList({ items, onChange }: { items: string[]; onChange: (v: string[]) => void }) {
  return (
    <div className="space-y-1">
      {items.map((b, i) => (
        <div key={i} className="flex gap-2">
          <span className="mt-2 text-[var(--muted-foreground)]">•</span>
          <input
            value={b}
            onChange={(e) => { const n = [...items]; n[i] = e.target.value; onChange(n); }}
            className="flex-1 rounded-md border border-[var(--border)] bg-[var(--muted)] px-3 py-1.5 text-sm focus:border-[var(--primary)] focus:outline-none"
          />
          <button onClick={() => onChange(items.filter((_, j) => j !== i))} className="text-xs text-red-400 hover:text-red-600">
            Remove
          </button>
        </div>
      ))}
      <button onClick={() => onChange([...items, ""])} className="text-xs text-[var(--primary)] hover:underline">
        + Add bullet
      </button>
    </div>
  );
}

function RemoveBtn({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} className="text-xs text-red-400 hover:text-red-600">
      Remove
    </button>
  );
}

/* ── types (matching backend) ────────────────────────── */
interface PersonalDetails { full_name: string; email: string; phone: string; location: string; linkedin_url: string; github_url: string; portfolio_url: string; }
interface Experience { company: string; role: string; location: string; start_date: string; end_date: string; current: boolean; bullets: string[]; }
interface Education { institution: string; degree: string; field: string; start_date: string; end_date: string; gpa: string; highlights: string[]; }
interface Project { name: string; description: string; tech_stack: string[]; url: string; bullets: string[]; }
interface SkillCategory { category: string; items: string[]; }
interface Certification { name: string; issuer: string; date: string; url: string; }

interface ResumeData {
  personal_details: PersonalDetails;
  summary: string;
  experience: Experience[];
  education: Education[];
  projects: Project[];
  skills: SkillCategory[];
  certifications: Certification[];
}

const EMPTY_RESUME: ResumeData = {
  personal_details: { full_name: "", email: "", phone: "", location: "", linkedin_url: "", github_url: "", portfolio_url: "" },
  summary: "",
  experience: [],
  education: [],
  projects: [],
  skills: [],
  certifications: [],
};

/* ── page ─────────────────────────────────────────────── */
export default function MyResumePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [resume, setResume] = useState<ResumeData>(EMPTY_RESUME);
  const [dirty, setDirty] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) {
        router.push("/onboarding");
      } else {
        setSessionReady(true);
      }
    });
  }, [router]);

  const { data, isLoading } = useQuery({
    queryKey: ["master-resume"],
    queryFn: getResume,
    enabled: sessionReady,
  });

  useEffect(() => {
    if (data) {
      setResume({
        personal_details: data.personal_details || EMPTY_RESUME.personal_details,
        summary: data.summary || "",
        experience: data.experience || [],
        education: data.education || [],
        projects: data.projects || [],
        skills: data.skills || [],
        certifications: data.certifications || [],
      });
    }
  }, [data]);

  /* generic updater */
  const update = useCallback(<K extends keyof ResumeData>(key: K, value: ResumeData[K]) => {
    setResume((r) => ({ ...r, [key]: value }));
    setDirty(true);
  }, []);

  const updatePersonal = useCallback((field: keyof PersonalDetails, value: string) => {
    setResume((r) => ({ ...r, personal_details: { ...r.personal_details, [field]: value } }));
    setDirty(true);
  }, []);

  /* save mutation */
  const saveMut = useMutation({
    mutationFn: () => saveResume(resume),
    onSuccess: () => { setDirty(false); queryClient.invalidateQueries({ queryKey: ["master-resume"] }); toast.success("Resume saved"); },
    onError: () => toast.error("Failed to save"),
  });

  /* PDF upload */
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const result = await uploadResumePDF(file);
      const r = result.resume;
      setResume({
        personal_details: r.personal_details || EMPTY_RESUME.personal_details,
        summary: r.summary || "",
        experience: r.experience || [],
        education: r.education || [],
        projects: r.projects || [],
        skills: r.skills || [],
        certifications: r.certifications || [],
      });
      setDirty(false);
      queryClient.invalidateQueries({ queryKey: ["master-resume"] });
      toast.success("Resume parsed and populated — review and edit as needed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  /* list helpers */
  const addExperience = () => update("experience", [...resume.experience, { company: "", role: "", location: "", start_date: "", end_date: "", current: false, bullets: [] }]);
  const addEducation = () => update("education", [...resume.education, { institution: "", degree: "", field: "", start_date: "", end_date: "", gpa: "", highlights: [] }]);
  const addProject = () => update("projects", [...resume.projects, { name: "", description: "", tech_stack: [], url: "", bullets: [] }]);
  const addSkillCat = () => update("skills", [...resume.skills, { category: "", items: [] }]);
  const addCert = () => update("certifications", [...resume.certifications, { name: "", issuer: "", date: "", url: "" }]);

  const updateListItem = <T,>(key: keyof ResumeData, index: number, patch: Partial<T>) => {
    setResume((r) => {
      const list = [...(r[key] as T[])];
      list[index] = { ...list[index], ...patch };
      return { ...r, [key]: list };
    });
    setDirty(true);
  };

  const removeListItem = (key: keyof ResumeData, index: number) => {
    setResume((r) => ({ ...r, [key]: (r[key] as unknown[]).filter((_, i) => i !== index) }));
    setDirty(true);
  };

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center text-[var(--muted-foreground)]">Loading resume...</div>;
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--background)] px-6 py-4">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => router.push("/dashboard")} className="text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]">
              &larr; Dashboard
            </button>
            <h1 className="text-xl font-bold">My Resume</h1>
          </div>
          <div className="flex items-center gap-3">
            <label className={`cursor-pointer rounded-lg border border-[var(--border)] px-4 py-2 text-sm hover:bg-[var(--muted)] ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
              {uploading ? "Parsing..." : "Upload PDF"}
              <input type="file" accept=".pdf" onChange={handleUpload} className="hidden" />
            </label>
            <button
              onClick={() => saveMut.mutate()}
              disabled={!dirty || saveMut.isPending}
              className="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-40"
            >
              {saveMut.isPending ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-4xl space-y-6 px-6 py-6">
        {/* Personal Details */}
        <Section title="Personal Details">
          <div className="grid grid-cols-2 gap-4">
            <Field label="Full Name" value={resume.personal_details.full_name} onChange={(v) => updatePersonal("full_name", v)} placeholder="John Doe" />
            <Field label="Email" value={resume.personal_details.email} onChange={(v) => updatePersonal("email", v)} placeholder="john@example.com" />
            <Field label="Phone" value={resume.personal_details.phone} onChange={(v) => updatePersonal("phone", v)} placeholder="+1 (555) 123-4567" />
            <Field label="Location" value={resume.personal_details.location} onChange={(v) => updatePersonal("location", v)} placeholder="San Francisco, CA" />
            <Field label="LinkedIn URL" value={resume.personal_details.linkedin_url} onChange={(v) => updatePersonal("linkedin_url", v)} placeholder="https://linkedin.com/in/..." />
            <Field label="GitHub URL" value={resume.personal_details.github_url} onChange={(v) => updatePersonal("github_url", v)} placeholder="https://github.com/..." />
            <Field label="Portfolio URL" value={resume.personal_details.portfolio_url} onChange={(v) => updatePersonal("portfolio_url", v)} placeholder="https://..." />
          </div>
        </Section>

        {/* Summary */}
        <Section title="Professional Summary">
          <Field label="" value={resume.summary} onChange={(v) => update("summary", v)} placeholder="Experienced software engineer with..." multiline />
        </Section>

        {/* Experience */}
        <Section title="Experience" onAdd={addExperience}>
          {resume.experience.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No experience added yet</p>}
          <div className="space-y-6">
            {resume.experience.map((exp, i) => (
              <div key={i} className="rounded-md border border-[var(--border)] p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-[var(--muted-foreground)]">Experience {i + 1}</span>
                  <RemoveBtn onClick={() => removeListItem("experience", i)} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Company" value={exp.company} onChange={(v) => updateListItem<Experience>("experience", i, { company: v })} />
                  <Field label="Role" value={exp.role} onChange={(v) => updateListItem<Experience>("experience", i, { role: v })} />
                  <Field label="Location" value={exp.location} onChange={(v) => updateListItem<Experience>("experience", i, { location: v })} />
                  <div className="grid grid-cols-2 gap-2">
                    <Field label="Start" value={exp.start_date} onChange={(v) => updateListItem<Experience>("experience", i, { start_date: v })} placeholder="Jan 2023" />
                    <Field label="End" value={exp.current ? "Present" : exp.end_date} onChange={(v) => updateListItem<Experience>("experience", i, v === "Present" ? { current: true, end_date: "" } : { current: false, end_date: v })} placeholder="Present" />
                  </div>
                </div>
                <div>
                  <span className="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Bullets</span>
                  <BulletList items={exp.bullets} onChange={(v) => updateListItem<Experience>("experience", i, { bullets: v })} />
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Education */}
        <Section title="Education" onAdd={addEducation}>
          {resume.education.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No education added yet</p>}
          <div className="space-y-6">
            {resume.education.map((edu, i) => (
              <div key={i} className="rounded-md border border-[var(--border)] p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-[var(--muted-foreground)]">Education {i + 1}</span>
                  <RemoveBtn onClick={() => removeListItem("education", i)} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Institution" value={edu.institution} onChange={(v) => updateListItem<Education>("education", i, { institution: v })} />
                  <Field label="Degree" value={edu.degree} onChange={(v) => updateListItem<Education>("education", i, { degree: v })} placeholder="B.S." />
                  <Field label="Field of Study" value={edu.field} onChange={(v) => updateListItem<Education>("education", i, { field: v })} placeholder="Computer Science" />
                  <Field label="GPA" value={edu.gpa} onChange={(v) => updateListItem<Education>("education", i, { gpa: v })} placeholder="3.8" />
                  <Field label="Start" value={edu.start_date} onChange={(v) => updateListItem<Education>("education", i, { start_date: v })} placeholder="Aug 2019" />
                  <Field label="End" value={edu.end_date} onChange={(v) => updateListItem<Education>("education", i, { end_date: v })} placeholder="May 2023" />
                </div>
                <div>
                  <span className="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Highlights</span>
                  <BulletList items={edu.highlights} onChange={(v) => updateListItem<Education>("education", i, { highlights: v })} />
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Projects */}
        <Section title="Projects" onAdd={addProject}>
          {resume.projects.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No projects added yet</p>}
          <div className="space-y-6">
            {resume.projects.map((proj, i) => (
              <div key={i} className="rounded-md border border-[var(--border)] p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-[var(--muted-foreground)]">Project {i + 1}</span>
                  <RemoveBtn onClick={() => removeListItem("projects", i)} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Name" value={proj.name} onChange={(v) => updateListItem<Project>("projects", i, { name: v })} />
                  <Field label="URL" value={proj.url} onChange={(v) => updateListItem<Project>("projects", i, { url: v })} placeholder="https://..." />
                </div>
                <Field label="Description" value={proj.description} onChange={(v) => updateListItem<Project>("projects", i, { description: v })} multiline />
                <div>
                  <span className="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Tech Stack (comma-separated)</span>
                  <input
                    value={proj.tech_stack.join(", ")}
                    onChange={(e) => updateListItem<Project>("projects", i, { tech_stack: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
                    className="w-full rounded-md border border-[var(--border)] bg-[var(--muted)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none"
                    placeholder="React, Node.js, PostgreSQL"
                  />
                </div>
                <div>
                  <span className="mb-1 block text-xs font-medium text-[var(--muted-foreground)]">Bullets</span>
                  <BulletList items={proj.bullets} onChange={(v) => updateListItem<Project>("projects", i, { bullets: v })} />
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Skills */}
        <Section title="Skills" onAdd={addSkillCat}>
          {resume.skills.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No skills added yet</p>}
          <div className="space-y-4">
            {resume.skills.map((cat, i) => (
              <div key={i} className="flex items-start gap-3">
                <input
                  value={cat.category}
                  onChange={(e) => updateListItem<SkillCategory>("skills", i, { category: e.target.value })}
                  placeholder="Category (e.g. Languages)"
                  className="w-40 shrink-0 rounded-md border border-[var(--border)] bg-[var(--muted)] px-3 py-2 text-sm font-medium focus:border-[var(--primary)] focus:outline-none"
                />
                <input
                  value={cat.items.join(", ")}
                  onChange={(e) => updateListItem<SkillCategory>("skills", i, { items: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
                  placeholder="Python, TypeScript, Go"
                  className="flex-1 rounded-md border border-[var(--border)] bg-[var(--muted)] px-3 py-2 text-sm focus:border-[var(--primary)] focus:outline-none"
                />
                <RemoveBtn onClick={() => removeListItem("skills", i)} />
              </div>
            ))}
          </div>
        </Section>

        {/* Certifications */}
        <Section title="Certifications" onAdd={addCert}>
          {resume.certifications.length === 0 && <p className="text-sm text-[var(--muted-foreground)]">No certifications added yet</p>}
          <div className="space-y-4">
            {resume.certifications.map((cert, i) => (
              <div key={i} className="rounded-md border border-[var(--border)] p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm font-medium text-[var(--muted-foreground)]">Certification {i + 1}</span>
                  <RemoveBtn onClick={() => removeListItem("certifications", i)} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Name" value={cert.name} onChange={(v) => updateListItem<Certification>("certifications", i, { name: v })} placeholder="AWS Solutions Architect" />
                  <Field label="Issuer" value={cert.issuer} onChange={(v) => updateListItem<Certification>("certifications", i, { issuer: v })} placeholder="Amazon Web Services" />
                  <Field label="Date" value={cert.date} onChange={(v) => updateListItem<Certification>("certifications", i, { date: v })} placeholder="Mar 2024" />
                  <Field label="URL" value={cert.url} onChange={(v) => updateListItem<Certification>("certifications", i, { url: v })} placeholder="https://..." />
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Bottom save */}
        <div className="flex justify-end pb-10">
          <button
            onClick={() => saveMut.mutate()}
            disabled={!dirty || saveMut.isPending}
            className="rounded-lg bg-[var(--primary)] px-6 py-3 font-medium text-[var(--primary-foreground)] disabled:opacity-40"
          >
            {saveMut.isPending ? "Saving..." : "Save Resume"}
          </button>
        </div>
      </div>
    </div>
  );
}
