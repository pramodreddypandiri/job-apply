# Local Development Setup

Everything runs on your machine. One-time setup, then two commands to start.

---

## Prerequisites

Install these before anything else:

```bash
# macOS (Homebrew)
brew install python@3.12 node@20 docker redis

# Python package manager
pip install uv    # faster than pip, use this for everything

# Node package manager
npm install -g pnpm

# Verify
python3 --version    # 3.12+
node --version       # 20+
docker --version     # 24+
```

---

## 1. Clone and structure

```bash
mkdir job-agent && cd job-agent

# Create structure
mkdir -p backend/{api/routes,api/middleware,agents,tasks,db,llm/prompts,models,utils}
mkdir -p frontend
touch backend/main.py
touch docker-compose.yml
touch .env
```

---

## 2. Python backend setup

```bash
cd backend

# Create virtual environment
uv venv .venv
source .venv/bin/activate    # or .venv\Scripts\activate on Windows

# Install dependencies
uv pip install \
  fastapi uvicorn[standard] \
  celery redis \
  playwright \
  anthropic \
  supabase \
  tavily-python \
  weasyprint \
  python-jose python-multipart \
  pydantic-settings \
  jinja2 \
  loguru sentry-sdk \
  httpx beautifulsoup4 \
  python-dotenv

# Install Playwright browsers
playwright install chromium

# Save requirements
uv pip freeze > requirements.txt
```

---

## 3. Next.js frontend setup

```bash
cd frontend
pnpm create next-app . --typescript --tailwind --app --src-dir=false

# Install additional packages
pnpm add \
  @supabase/ssr @supabase/supabase-js \
  @tanstack/react-query \
  sonner \
  lucide-react \
  clsx tailwind-merge \
  @radix-ui/react-dialog @radix-ui/react-accordion
```

---

## 4. Docker Compose

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    env_file: .env
    network_mode: host    # needed to reach Chrome on localhost:9222
    depends_on:
      - redis

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A tasks.celery_app worker --loglevel=info --concurrency=2
    volumes:
      - ./backend:/app
    env_file: .env
    network_mode: host
    depends_on:
      - redis

  beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A tasks.celery_app beat --loglevel=info
    volumes:
      - ./backend:/app
    env_file: .env
    depends_on:
      - redis

volumes:
  redis_data:
```

---

## 5. Backend Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps for Playwright + WeasyPrint
RUN apt-get update && apt-get install -y \
    wget curl \
    libglib2.0-0 libnss3 libnspr4 libatk1.0-0 \
    libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .
```

---

## 6. Environment variables

```bash
# .env (copy this, fill in values)

# ─── Supabase ───────────────────────────────────────
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...          # Settings > API > service_role (keep secret)
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ... # Settings > API > anon/public

# ─── Claude ─────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...

# ─── Tavily ─────────────────────────────────────────
TAVILY_API_KEY=tvly-...

# ─── Gmail OAuth ────────────────────────────────────
# Create at console.cloud.google.com → APIs > Gmail API > Credentials
GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-...
GMAIL_REDIRECT_URI=http://localhost:8000/auth/gmail/callback

# ─── GitHub ─────────────────────────────────────────
# Create at github.com/settings/tokens (read:user, repo scopes)
GITHUB_TOKEN=ghp_...

# ─── Browser ────────────────────────────────────────
CHROME_DEBUG_PORT=9222

# ─── Redis ──────────────────────────────────────────
REDIS_URL=redis://localhost:6379

# ─── App ────────────────────────────────────────────
SECRET_KEY=your-random-32-char-string-here
ENVIRONMENT=development

# ─── Sentry (optional) ──────────────────────────────
SENTRY_DSN=https://...@sentry.io/...

# ─── Frontend ───────────────────────────────────────
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 7. Supabase setup

1. Create project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** and run all migrations from `docs/DATABASE.md`
3. Enable **pgvector** extension: Extensions tab → search pgvector → enable
4. Enable **Realtime** on `tracker_events` table: Database → Replication → enable table
5. Set up **RLS policies** (copy from DATABASE.md)
6. Go to **Storage** → create bucket called `resumes` (private)
7. Add storage policy: users can read/write their own folder only

---

## 8. Gmail API setup

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create new project "job-agent"
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Web application)
5. Add `http://localhost:8000/auth/gmail/callback` to authorised redirect URIs
6. Copy Client ID and Secret to `.env`

Scopes needed:
```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.send
```

---

## 9. FastAPI entry point

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sentry_sdk
from loguru import logger
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_url: str
    supabase_service_key: str
    anthropic_api_key: str
    redis_url: str = "redis://localhost:6379"
    chrome_debug_port: int = 9222
    environment: str = "development"
    sentry_dsn: str = ""

    class Config:
        env_file = ".env"

settings = Settings()

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)

app = FastAPI(title="Job Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from api.routes import profile, applications, prepare, tasks, auth
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(applications.router, prefix="/applications", tags=["applications"])
app.include_router(prepare.router, prefix="/prepare", tags=["prepare"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## 10. Daily dev workflow

```bash
# Terminal 1 — Chrome with debug port
open -a "Google Chrome" --args --remote-debugging-port=9222
# or add alias to ~/.zshrc: alias chrome-dev='open -a "Google Chrome" --args --remote-debugging-port=9222'

# Terminal 2 — Backend stack
docker-compose up

# Terminal 3 — Frontend
cd frontend && pnpm dev

# App: http://localhost:3000
# API: http://localhost:8000
# API docs: http://localhost:8000/docs   ← FastAPI auto-docs, very useful
# Redis: redis-cli ping
```

---

## Useful dev commands

```bash
# Watch Celery task logs
docker-compose logs -f worker

# Watch Gmail polling logs
docker-compose logs -f beat

# Restart just the API (after code change, if not using --reload)
docker-compose restart api

# Run a one-off Celery task manually (testing)
docker-compose exec worker celery -A tasks.celery_app call tasks.application.parse_jd --args='["test-id"]'

# Open Supabase table editor
# supabase.com → your project → Table Editor

# Test Claude connection
python -c "import anthropic; c = anthropic.Anthropic(); print(c.messages.create(model='claude-haiku-4-5-20251001', max_tokens=10, messages=[{'role':'user','content':'hi'}]).content[0].text)"
```
