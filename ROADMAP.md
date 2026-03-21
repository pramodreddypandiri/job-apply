# Build Roadmap

Milestone-based build order. Each milestone is independently usable.
Build in order — each layer depends on the previous one.

---

## Milestone 0 — Foundation (Day 1–2)

Get the skeleton running end-to-end before building any features.

```
[ ] Supabase project created
[ ] All migrations run (DATABASE.md)
[ ] pgvector enabled
[ ] RLS policies applied
[ ] docker-compose up works (API + worker + beat + redis all healthy)
[ ] FastAPI /health returns 200
[ ] Next.js app boots at localhost:3000
[ ] Supabase Auth working (Google OAuth login/logout)
[ ] JWT middleware on FastAPI validates Supabase tokens
[ ] .env populated with all keys
[ ] Loguru logging configured
[ ] Sentry connected (optional but worth doing now)
```

**Test:** Log in with Google → hit `GET /profile` → get 200 with empty profile.

---

## Milestone 1 — Onboarding + Skill Graph (Day 3–5)

User can sign up, upload resume, connect GitHub, see their skill graph.

```
[ ] POST /profile/onboard
    [ ] Accept resume PDF upload
    [ ] Store target roles, locations, seniority floor
    [ ] Upload resume PDF to Supabase Storage
    [ ] Parse resume text with Haiku (extract skills, experience, timeline)
    [ ] Seed skill_graph table from resume

[ ] Profile analyser — GitHub
    [ ] Connect GitHub token from user
    [ ] Fetch repos via GitHub API
    [ ] Calculate depth score per repo (ownership, longevity, recency)
    [ ] Extract tech stack per repo
    [ ] Upsert into skill_graph

[ ] Profile analyser — Portfolio
    [ ] Fetch portfolio URL with httpx
    [ ] Extract case studies and tech mentions with Haiku
    [ ] Merge into skill_graph

[ ] POST /profile/analyse (enqueue Celery task)
[ ] GET /profile/skill-graph (return full graph)

[ ] Frontend: /onboarding page
    [ ] Resume upload
    [ ] Target roles input
    [ ] GitHub username input
    [ ] Portfolio URL input
    [ ] "Analyse my profile" button + loading state

[ ] Frontend: /profile page
    [ ] Skill graph display grouped by category
    [ ] Depth bars (1-5)
    [ ] Source badges (github / resume / portfolio)
    [ ] Nudge up/down buttons
```

**Test:** Complete onboarding → skill graph populated with real skills from your GitHub.

---

## Milestone 2 — Core Application Pipeline (Day 6–12)

The main value prop. Paste URL → tailored resume → submit.

```
[ ] Deduplication
    [ ] POST /applications/check
    [ ] URL normalisation (strip tracking params)
    [ ] Role fingerprint generation
    [ ] Tracker lookup (URL match + fingerprint match)
    [ ] Return correct status + application if found

[ ] JD Parser agent
    [ ] Fetch URL content (httpx + BeautifulSoup)
    [ ] Handle JS-rendered pages (Playwright fallback)
    [ ] Extract structured JD with Haiku
    [ ] Detect ATS type from URL patterns
    [ ] Store parsed JD in applications table

[ ] Narrative Aligner agent
    [ ] Load user's master resume + skill graph
    [ ] Identify eligible side projects (depth >= 3, interview_defensible)
    [ ] Generate tailored resume with Sonnet
    [ ] Parse changes_summary from response
    [ ] Calculate pct_changed and jd_overlap_score

[ ] Authenticity Guard
    [ ] Compare original vs tailored
    [ ] Block if hallucination detected
    [ ] Store guard result

[ ] Resume PDF generation
    [ ] HTML template for resume (ATS-safe: no tables, no columns, simple fonts)
    [ ] WeasyPrint HTML → PDF
    [ ] Upload to Supabase Storage

[ ] Review Gate
    [ ] GET /applications/:id/resume/diff
    [ ] Frontend: /apply/review/[id]
        [ ] Side-by-side diff view
        [ ] Changes summary cards
        [ ] "% changed" badge
        [ ] Approve / Edit / Discard buttons

[ ] Form Fill agent
    [ ] Playwright connects to Chrome via CDP
    [ ] ATS detection (Greenhouse, Lever, Workday, generic)
    [ ] Field mapping per ATS type
    [ ] Resume PDF upload
    [ ] Human typing simulation (random delays)
    [ ] Escalation on CAPTCHA / login required
    [ ] Screenshot capture pre + post submit
    [ ] Status: needs_action on failure

[ ] POST /applications/start (full Celery chain)
[ ] POST /applications/:id/approve (triggers form fill)
[ ] GET /applications/:id/status (polling endpoint)

[ ] Frontend: /apply page
    [ ] URL paste input
    [ ] Dedup check on blur/paste
    [ ] Duplicate alert component
    [ ] Instructions textarea
    [ ] Start button
    [ ] Processing status steps
```

**Test:** Paste a real Greenhouse job URL → see tailored resume → approve → watch form fill.

---

## Milestone 3 — Job Tracker + Gmail Monitor (Day 13–17)

Applications tracked automatically. Status updates without manual input.

```
[ ] Gmail OAuth flow
    [ ] GET /auth/gmail/connect → redirect to Google
    [ ] GET /auth/gmail/callback → store refresh token

[ ] Gmail monitor
    [ ] Gmail API client (fetch unread from inbox)
    [ ] Email classifier agent (Haiku)
    [ ] Map classification to application (by company name match)
    [ ] Update application status in DB
    [ ] Create tracker_event record
    [ ] Celery Beat: poll every 5 minutes

[ ] Tracker events
    [ ] Append-only event log per application
    [ ] Handle: confirmed, viewed, interview_invite, rejection, offer

[ ] Resume lifecycle
    [ ] On rejection: trash resume (delete PDF from storage, keep metadata)
    [ ] On interview: mark resume status = active
    [ ] 90-day auto-expiry for pending applications (Celery Beat task)

[ ] Frontend: /dashboard
    [ ] Application cards with status
    [ ] Supabase Realtime subscription on tracker_events
    [ ] Toast notifications for new events
    [ ] Application detail drawer
    [ ] Event timeline per application
    [ ] Filter by status
```

**Test:** Submit application → reject it manually in DB → check resume is trashed.
**Test:** Receive a real application email → check tracker updates automatically.

---

## Milestone 4 — Interview Prep (Day 18–23)

When an invite arrives, a prep plan is ready within minutes.

```
[ ] Interview type detector
    [ ] Parse email + calendar invite
    [ ] Detect: coding / system_design / behavioural / panel
    [ ] Confidence score
    [ ] Extract interview date

[ ] Research agent
    [ ] Tavily searches (Glassdoor, Reddit, LeetCode, company blog)
    [ ] Extract question patterns from results
    [ ] Summarise interview process
    [ ] Rate limiting (don't hammer Tavily)

[ ] Prep plan generator
    [ ] Sonnet with research + skill graph + resume claims
    [ ] Day-by-day schedule (respects days available)
    [ ] STAR story generation from user's projects
    [ ] Gap topics identification
    [ ] Claims to defend (from tailored resume)

[ ] Triggered automatically from Gmail: interview_invite classification
    [ ] Celery task: trigger_interview_prep(application_id)

[ ] GET /applications/:id/prep
[ ] Frontend: /prep/[applicationId]
    [ ] Interview summary header
    [ ] Day accordion
    [ ] STAR stories expandable
    [ ] Claims to defend section
    [ ] Gap topics list with resource links
    [ ] Days remaining countdown
```

**Test:** Manually trigger prep plan for one of your applications → review quality.

---

## Milestone 5 — Prepare Page (Day 24–30)

Daily skill building. The habit-forming layer.

```
[ ] Topic curriculum generation
    [ ] Define topic list per role type (hardcode for "Senior Backend Engineer" first)
    [ ] Map topics to skill_graph entries
    [ ] Gap identification: topics in curriculum not in skill graph at depth >= 3

[ ] Daily session logic
    [ ] Pick today's topic: prioritise gaps, respect spaced repetition schedule
    [ ] Generate concept brief with Sonnet (pitched at user's current depth)
    [ ] Generate 3-5 practice questions with Sonnet (mix conceptual + applied)
    [ ] Generate model answers

[ ] Spaced repetition
    [ ] next_review calculation from self-rating
    [ ] Update skill_graph depth on consecutive got_it ratings

[ ] GET /prepare/today
[ ] GET /prepare/today/answer/:question_id
[ ] POST /prepare/today/rate
[ ] GET /prepare/topics

[ ] Frontend: /prepare
    [ ] Topic header + category badge
    [ ] Concept brief (collapsible)
    [ ] Question cards (one at a time)
    [ ] "See answer" reveal
    [ ] Rating buttons
    [ ] Session summary (streak, depth change, next review count)
    [ ] Topics overview page (progress by category)
```

**Test:** Complete a full session → check skill graph depth updated → see topic in spaced repetition.

---

## Post-MVP improvements (do these after you've used it for a week)

```
[ ] Cover letter generation (add to Milestone 2 pipeline)
[ ] LinkedIn URL scraping (add to profile analyser)
[ ] Better ATS handling (fix Workday quirks as you encounter them)
[ ] Resume template system (multiple visual formats)
[ ] Application analytics (which roles/skills get interviews)
[ ] Per-user tailoring fingerprint (learn from winning resumes)
[ ] Email draft for outreach (if you want to add the network agent later)
```

---

## File creation order

Start each milestone by creating empty files first, then fill them in:

```bash
# Milestone 1 files to create
touch backend/agents/profile_analyser.py
touch backend/api/routes/profile.py
touch backend/models/profile.py
touch backend/llm/prompts/resume_parser.j2
touch backend/llm/prompts/skill_extractor.j2

# Milestone 2 files to create
touch backend/agents/jd_parser.py
touch backend/agents/narrative.py
touch backend/agents/auth_guard.py
touch backend/agents/form_fill.py
touch backend/agents/deduplicator.py
touch backend/api/routes/applications.py
touch backend/models/application.py
touch backend/tasks/application.py
touch backend/utils/pdf.py
touch backend/utils/browser.py
touch backend/llm/prompts/jd_parser.j2
touch backend/llm/prompts/narrative_aligner.j2
touch backend/llm/prompts/auth_guard.j2

# ... and so on per milestone
```

---

## Definition of done per milestone

Each milestone is done when:
1. The feature works end-to-end with your real data
2. Errors surface as proper API error responses (not 500s)
3. The relevant Celery tasks retry correctly on failure
4. The frontend shows meaningful feedback at every step

Don't move to the next milestone until the current one meets this bar.
It's better to have a reliable 3-milestone system than a flaky 5-milestone one.
