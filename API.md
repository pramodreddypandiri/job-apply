# API Routes — FastAPI

Base URL: `http://localhost:8000`
All routes except `/health` and `/auth/*` require `Authorization: Bearer <supabase_jwt>` header.

---

## Auth

### `GET /health`
No auth. Returns `{"status": "ok"}`. Use for UptimeRobot monitoring.

### `GET /auth/gmail/connect`
Redirects user to Google OAuth consent screen for Gmail access.

### `GET /auth/gmail/callback`
Handles OAuth callback. Stores refresh token encrypted in `users_profile`.

---

## Profile

### `GET /profile`
Returns the current user's full profile including skill graph summary.

```python
# Response
{
  "id": "uuid",
  "full_name": "...",
  "target_roles": ["Senior Backend Engineer"],
  "skill_graph_summary": {
    "total_skills": 42,
    "avg_depth": 2.8,
    "gaps": ["distributed tracing", "consensus algorithms"],
    "strengths": ["Redis", "PostgreSQL", "FastAPI"]
  },
  "onboarded": true
}
```

### `POST /profile/onboard`
Initial onboarding — stores target roles, uploads resume PDF, connects integrations.

```python
# Request (multipart/form-data)
{
  "target_roles": ["Senior Backend Engineer", "Staff Engineer"],
  "target_locations": ["Remote", "London"],
  "seniority_floor": "senior",
  "excluded_keywords": ["frontend", "mobile"],
  "resume_pdf": <file>,
  "linkedin_url": "https://linkedin.com/in/...",
  "github_username": "...",
  "portfolio_url": "https://..."
}
```

### `POST /profile/analyse`
Triggers background profile analysis (GitHub + LinkedIn + portfolio).
Enqueues Celery task. Returns task ID.

```python
# Response
{"task_id": "uuid", "status": "queued"}
```

### `GET /profile/skill-graph`
Returns full skill graph with depth scores and STAR scaffolds.

```python
# Response
{
  "skills": [
    {
      "skill_name": "Redis",
      "category": "stack",
      "depth": 4,
      "source": ["github", "linkedin"],
      "ownership_level": "author",
      "interview_defensible": true,
      "star_scaffold": "Situation: needed async job queue..."
    }
  ]
}
```

### `PATCH /profile/skill-graph/:skill_name`
User manually adjusts a skill depth (nudge up/down from Prepare page).

```python
# Request
{"depth": 3}
```

---

## Applications

### `POST /applications/check`
Deduplication check before starting an application.
Call this the moment user pastes a URL — before showing the apply UI.

```python
# Request
{"url": "https://greenhouse.io/jobs/notion/senior-backend"}

# Response — no match
{"status": "new", "canonical_url": "...", "role": null}

# Response — match found
{
  "status": "duplicate",                    # or 'processing' | 'needs_action' | 'applied' | 'rejected_reposted'
  "application": {
    "id": "uuid",
    "company_name": "Notion",
    "role_title": "Senior Backend Engineer",
    "status": "applied",
    "submitted_at": "2025-03-01T...",
    "resume_id": "uuid"
  },
  "message": "You applied on March 1. Status: applied."
}
```

### `POST /applications/start`
Starts the full application pipeline. Enqueues Celery task chain.

```python
# Request
{
  "url": "https://greenhouse.io/jobs/notion/senior-backend",
  "instructions": "Emphasise distributed systems work",
  "referral_context": "Shared by Jane Smith on LinkedIn"    # optional
}

# Response
{
  "application_id": "uuid",
  "task_id": "uuid",
  "status": "processing"
}
```

### `GET /applications`
List all applications for the user.

```python
# Query params: status, limit, offset
# Response
{
  "applications": [
    {
      "id": "uuid",
      "company_name": "Notion",
      "role_title": "Senior Backend Engineer",
      "status": "interview",
      "submitted_at": "...",
      "updated_at": "...",
      "jd_overlap_score": 0.78
    }
  ],
  "total": 12
}
```

### `GET /applications/:id`
Full detail for one application including resume diff and events.

```python
# Response
{
  "application": {...},
  "resume": {
    "id": "uuid",
    "changes_summary": [...],
    "pct_changed": 23.4,
    "skills_elevated": ["Redis Streams"],
    "cover_letter_text": "..."
  },
  "events": [
    {"event_type": "applied", "created_at": "..."},
    {"event_type": "email_interview_invite", "created_at": "..."}
  ]
}
```

### `POST /applications/:id/approve`
User approves the tailored resume and cover letter. Triggers form fill agent.

```python
# Request — optional edits before approval
{
  "resume_text": "...",         # if user edited
  "cover_letter_text": "..."    # if user edited
}
```

### `POST /applications/:id/discard`
User discards the application before submission.

### `GET /applications/:id/status`
Lightweight status poll for the tracker UI.

```python
# Response
{
  "status": "processing",
  "step": "filling_form",      # 'parsing_jd' | 'tailoring' | 'review_pending' | 'filling_form' | 'submitted'
  "progress": 75               # 0-100
}
```

---

## Resume

### `GET /applications/:id/resume/diff`
Returns a structured diff of tailored vs master resume for the review gate UI.

```python
# Response
{
  "sections": [
    {
      "section": "experience",
      "items": [
        {
          "type": "reframed",
          "original": "Built REST APIs with FastAPI",
          "new": "Designed and shipped high-throughput REST APIs with FastAPI handling 50k req/day",
          "reason": "JD emphasises scale and throughput"
        },
        {
          "type": "elevated",
          "original": null,
          "new": "Built Redis Streams job queue processing 50k events/day (personal project)",
          "reason": "JD requires distributed systems experience — depth score 4, interview-defensible"
        }
      ]
    }
  ],
  "pct_changed": 23.4,
  "skills_added": ["Redis Streams", "distributed systems"],
  "jd_overlap_score": 0.78
}
```

---

## Interview Prep

### `GET /applications/:id/prep`
Returns the full prep plan for an application.

```python
# Response
{
  "interview_type": ["system_design", "behavioural"],
  "interview_date": "2025-03-15T...",
  "process_summary": "Two rounds: 1h system design, 45min behavioural with EM",
  "question_patterns": [
    {"topic": "distributed caching", "frequency": 8, "example_questions": ["..."]}
  ],
  "prep_plan": {
    "days": [
      {
        "day": 1,
        "focus": "Distributed caching deep dive",
        "tasks": ["Read Redis Streams docs", "Practice design: URL shortener"],
        "resources": [{"title": "...", "url": "..."}]
      }
    ]
  },
  "star_stories": [
    {
      "theme": "handling_scale",
      "project": "redis-queue-project",
      "situation": "...",
      "task": "...",
      "action": "...",
      "result": "..."
    }
  ],
  "gap_topics": ["Raft consensus", "vector clocks"],
  "claims_to_defend": [
    "Designed distributed job queue handling 50k events/day"
  ]
}
```

---

## Prepare Page

### `GET /prepare/today`
Returns today's topic and session items. Picks based on gap priority + spaced repetition schedule.

```python
# Response
{
  "topic": "Consistent Hashing",
  "category": "system_design",
  "current_depth": 2,
  "brief": "Consistent hashing solves the problem of...",  # ~500 word concept brief
  "questions": [
    {
      "id": "uuid",
      "question": "What problem does consistent hashing solve?",
      "type": "conceptual"
    },
    {
      "id": "uuid",
      "question": "You're designing a distributed cache with 10 nodes. A node goes down. How do you minimise cache misses?",
      "type": "applied"
    }
  ],
  "streak": 7,
  "sessions_this_week": 5
}
```

### `GET /prepare/today/answer/:question_id`
Returns the model answer for a question (shown after user has attempted it).

```python
# Response
{"answer": "Consistent hashing places both cache nodes and keys on a ring..."}
```

### `POST /prepare/today/rate`
Submits self-ratings for all questions in today's session.

```python
# Request
{
  "topic": "Consistent Hashing",
  "ratings": [
    {"question_id": "uuid", "rating": "got_it"},
    {"question_id": "uuid", "rating": "unsure"}
  ]
}

# Response — updated skill depth + next session topic
{
  "depth_updated": {"from": 2, "to": 2},   # only upgrades on 'got_it' 3x consecutive
  "next_review_items": 3,
  "message": "Good session. 3 items due for review tomorrow."
}
```

### `GET /prepare/topics`
Returns all topics grouped by category with progress for the current user.

```python
# Response
{
  "categories": [
    {
      "name": "system_design",
      "label": "System Design",
      "topics": [
        {
          "name": "Consistent Hashing",
          "depth": 2,
          "last_practiced": "2025-03-10",
          "next_review": "2025-03-12",
          "status": "due"    # 'due' | 'upcoming' | 'strong' | 'new'
        }
      ]
    }
  ]
}
```

---

## Tasks (internal — used by frontend polling)

### `GET /tasks/:task_id`
Returns Celery task status. Used by TanStack Query to poll application progress.

```python
# Response
{
  "task_id": "uuid",
  "status": "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY",
  "result": {...},     # if SUCCESS
  "error": "...",      # if FAILURE
  "progress": 60       # 0-100 if STARTED
}
```

---

## Error responses

All errors follow this shape:

```python
{
  "error": {
    "code": "DUPLICATE_APPLICATION",
    "message": "You already applied to this role on March 1.",
    "details": {"application_id": "uuid"}
  }
}
```

| Code | HTTP | Meaning |
|---|---|---|
| `DUPLICATE_APPLICATION` | 409 | Role already in tracker |
| `APPLICATION_IN_PROGRESS` | 409 | Same role being processed right now |
| `JD_PARSE_FAILED` | 422 | Could not extract JD from URL |
| `FORM_FILL_FAILED` | 500 | Playwright agent failed during submission |
| `CAPTCHA_REQUIRED` | 503 | ATS presented CAPTCHA — needs human |
| `LOGIN_REQUIRED` | 503 | ATS requires account login |
| `GMAIL_NOT_CONNECTED` | 403 | Gmail OAuth not completed |
