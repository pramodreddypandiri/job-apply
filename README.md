# Job Application Intelligence Platform

An AI-powered job application system that tailors resumes, fills forms, tracks applications, monitors emails, and builds interview prep — all running locally on your machine.

## What it does

- **Paste a job URL** → agent parses the JD, tailors your resume, fills the application form, submits it
- **Gmail monitor** → watches for interview invites, rejections, offers and updates tracker automatically
- **Interview prep** → when an invite arrives, researches the company's interview process and builds a personalised day-by-day prep plan
- **Prepare page** → daily 20-min skill building sessions based on your target role and current skill gaps
- **Profile intelligence** → analyses your GitHub, LinkedIn, portfolio to build a skill graph — no manual input

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 + TypeScript + TanStack Query |
| Backend API | FastAPI (Python) |
| Task Queue | Celery + Redis |
| Browser Automation | Playwright (Python) |
| Database | Supabase (Postgres + Auth + Storage + Realtime) |
| AI | Claude API (Sonnet for generation, Haiku for extraction) |
| Web Search | Tavily API |
| PDF Generation | WeasyPrint |
| Logging | Loguru |
| Error Tracking | Sentry |

## Running locally

```bash
# 1. Start Chrome with debug port (do this first, every session)
alias chrome-dev='open -a "Google Chrome" --args --remote-debugging-port=9222'
chrome-dev

# 2. Start the agent stack
docker-compose up

# 3. Frontend (separate terminal)
cd frontend && npm run dev
```

App runs at `http://localhost:3000`. API at `http://localhost:8000`.

## Repository structure

```
/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── api/
│   │   ├── routes/              # All route handlers
│   │   └── middleware/          # Auth, logging
│   ├── agents/
│   │   ├── jd_parser.py         # Job description extraction
│   │   ├── narrative.py         # Resume narrative alignment
│   │   ├── ats_optimizer.py     # ATS scoring and formatting
│   │   ├── form_fill.py         # Playwright form fill agent
│   │   ├── gmail_monitor.py     # Gmail polling and classification
│   │   ├── interview_prep.py    # Prep plan generation
│   │   ├── profile_analyser.py  # GitHub/LinkedIn/portfolio analysis
│   │   └── deduplicator.py      # Role fingerprint and lookup
│   ├── tasks/
│   │   ├── celery_app.py        # Celery configuration
│   │   ├── application.py       # Application pipeline tasks
│   │   ├── gmail.py             # Gmail polling tasks
│   │   └── profile.py           # Profile refresh tasks
│   ├── db/
│   │   ├── client.py            # Supabase client
│   │   └── queries.py           # Typed query helpers
│   ├── llm/
│   │   ├── client.py            # Claude API client
│   │   ├── prompts/             # Jinja2 prompt templates
│   │   └── structured.py       # JSON mode helpers
│   ├── models/                  # Pydantic schemas
│   └── utils/
│       ├── pdf.py               # WeasyPrint resume PDF
│       └── browser.py           # Playwright session manager
├── frontend/
│   ├── app/                     # Next.js app router
│   │   ├── dashboard/           # Job tracker
│   │   ├── apply/               # URL paste + review gate
│   │   ├── prepare/             # Daily prep page
│   │   └── profile/             # Skill graph view
│   ├── components/
│   └── lib/
│       ├── supabase.ts          # Supabase client
│       └── api.ts               # Backend API calls
├── docker-compose.yml
├── .env.example
└── docs/                        # This documentation
```

## Environment variables

Copy `.env.example` to `.env` and fill in:

```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=...          # backend — service role key
SUPABASE_ANON_KEY=...             # frontend — anon key

# Claude
ANTHROPIC_API_KEY=sk-ant-...

# Tavily
TAVILY_API_KEY=tvly-...

# Gmail OAuth
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REDIRECT_URI=http://localhost:8000/auth/gmail/callback

# GitHub
GITHUB_TOKEN=ghp_...              # personal access token, read:user scope

# Browser
CHROME_DEBUG_PORT=9222

# Redis
REDIS_URL=redis://localhost:6379

# Sentry (optional)
SENTRY_DSN=...
```
