# Architecture Overview

## System layers

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND  (Next.js · Vercel)                                   │
│  /dashboard  /apply  /prepare  /prep/[id]  /profile             │
│  TanStack Query · Supabase Realtime · sonner toasts             │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP + JWT
┌─────────────────▼───────────────────────────────────────────────┐
│  API  (FastAPI · localhost:8000)                                 │
│  Auth middleware → validates Supabase JWT on every request       │
│  Routes: /profile  /applications  /prepare  /tasks  /auth       │
└────────┬────────────────────────────────────┬───────────────────┘
         │ enqueue tasks                       │ read/write
┌────────▼────────────┐             ┌──────────▼──────────────────┐
│  TASK QUEUE         │             │  DATABASE  (Supabase)        │
│  Celery + Redis     │             │  Postgres + pgvector         │
│  workers: 2         │             │  Storage (resume PDFs)       │
│  beat: every 5min   │             │  Realtime (tracker events)   │
└────────┬────────────┘             │  Auth (Google OAuth)         │
         │ executes                 └─────────────────────────────┘
┌────────▼────────────────────────────────────────────────────────┐
│  AGENTS  (Python)                                               │
│                                                                 │
│  jd_parser        → Haiku  → structured JD from URL            │
│  narrative        → Sonnet → tailored resume                    │
│  auth_guard       → Haiku  → hallucination check               │
│  form_fill        → Playwright → fills and submits form         │
│  gmail_monitor    → Haiku  → classifies incoming emails         │
│  interview_prep   → Sonnet → research + prep plan               │
│  profile_analyser → Haiku  → GitHub/portfolio skill extraction  │
│  deduplicator     → Haiku  → fingerprint matching               │
└────────┬────────────────────┬───────────────────────────────────┘
         │                    │
┌────────▼──────┐    ┌────────▼────────────────────────────────────┐
│  CLAUDE API   │    │  EXTERNAL SERVICES                           │
│  Haiku/Sonnet │    │  GitHub API · Gmail API · Tavily · WeasyPrint│
└───────────────┘    └─────────────────────────────────────────────┘
         │
┌────────▼──────────────────────────────────────────────────────┐
│  BROWSER  (Chrome on your machine · port 9222)                │
│  Playwright attaches via CDP                                  │
│  Real session · Real fingerprint · Human-like pacing          │
└───────────────────────────────────────────────────────────────┘
```

---

## Data flow: application pipeline

```
User pastes URL
      │
      ▼
POST /applications/check
      │
      ├── duplicate found → return status, block
      │
      └── new role → POST /applications/start
                          │
                          ▼
                    Celery chain starts:
                          │
                    [1] parse_jd.task
                          │  fetch URL → extract JD → detect ATS
                          │  write: applications.jd_raw, jd_parsed
                          ▼
                    [2] align_narrative.task
                          │  load skill graph → generate tailored resume
                          │  write: resumes (draft)
                          ▼
                    [3] run_auth_guard.task
                          │  check for hallucinations
                          │  update: resumes.status
                          ▼
                    [4] generate_pdf.task
                          │  HTML → PDF → upload to Storage
                          │  write: resumes.resume_pdf_url
                          ▼
                    status = 'review_pending'
                    ← frontend polling detects this
                    ← UI shows diff + approval gate
                          │
                    User approves
                          │
                          ▼
                    POST /applications/:id/approve
                          │
                          ▼
                    [5] fill_form.task
                          │  Playwright → navigate → fill → submit
                          │  write: applications.status = 'applied'
                          │         applications.submitted_at
                          │         tracker_events (applied)
                          ▼
                    Supabase Realtime fires
                    ← frontend card updates live
```

---

## Data flow: Gmail monitor

```
Celery Beat: every 5 minutes
      │
      ▼
poll_gmail.task
      │
      ├── fetch unread emails from Gmail API
      │
      ▼
for each email:
      │
      ▼
classify_email.task (Haiku)
      │
      ├── unrelated → skip
      │
      ├── confirmed → update applications.status = 'applied'
      │
      ├── viewed → create tracker_event
      │
      ├── interview_invite →
      │         update applications.status = 'interview'
      │         create tracker_event
      │         trigger_interview_prep.task(application_id)
      │                   │
      │                   ▼
      │         [async] interview_prep pipeline
      │                   detect type → research → generate plan
      │                   write: interview_prep table
      │
      ├── rejection →
      │         update applications.status = 'rejected'
      │         create tracker_event
      │         trash_resume.task(application_id)
      │                   │
      │                   ▼
      │         delete PDF from Storage
      │         keep metadata in resumes table
      │
      └── offer →
                update applications.status = 'offer'
                mark resume status = 'archived'
```

---

## Key design decisions

**Why Celery over FastAPI background tasks?**
FastAPI `BackgroundTasks` are not durable — if the server restarts mid-task, the task is lost silently. Celery tasks are stored in Redis, survive restarts, and are retryable. For a form-fill that takes 8 minutes, durability is non-negotiable.

**Why Supabase Realtime over polling?**
Tracker cards update the moment a Gmail event is processed — no 3-second polling lag. The Postgres change triggers the Realtime subscription directly.

**Why two Claude models?**
Haiku is ~20x cheaper than Sonnet and fast enough for extraction tasks (classify email, parse JD, check dedup). Sonnet's quality is only needed for generation (resume writing, prep plan, concept briefs). On 100 applications/month this saves ~$80/mo.

**Why Playwright on local Chrome (not headless)?**
LinkedIn and most ATS systems fingerprint browser environments. A headless Chromium on a server with a different IP than the registered session gets flagged. Running on your local Chrome with your session cookies means every request looks identical to your normal browsing.

**Why WeasyPrint for PDF?**
Generates ATS-safe PDFs from HTML templates. No tables, no text boxes, no columns — just clean HTML that Workday, Greenhouse, and Taleo can parse reliably. Also free.

---

## Error handling philosophy

Every agent should fail loudly, not silently.

```
Agent failure →
  update application.status = 'needs_action'
  create tracker_event with error details
  Supabase Realtime fires
  frontend shows "Agent needs your help" toast
  user sees what failed and what to do manually
```

Never drop a failure into a log file and move on. The user needs to know.

---

## Security notes

- `SUPABASE_SERVICE_KEY` only ever used in backend — never exposed to frontend
- Frontend uses `SUPABASE_ANON_KEY` with RLS — users can only see their own rows
- Gmail tokens stored encrypted (use `python-jose` to encrypt at rest)
- Chrome debug port (9222) only accessible on localhost — not exposed to network
- All LLM prompts include user data — never log full prompt content in production
