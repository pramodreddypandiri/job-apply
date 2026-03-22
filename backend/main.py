from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from backend.config import get_settings
from backend.db.client import init_supabase

settings = get_settings()

# Configure loguru
logger.remove()
logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}")

# Sentry
if settings.sentry_dsn:
    import sentry_sdk
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)

# Initialize Supabase client
init_supabase()

app = FastAPI(title="Job Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from backend.api.routes import profile, applications, prepare, tasks, auth, resume

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(resume.router, prefix="/resume", tags=["resume"])
app.include_router(applications.router, prefix="/applications", tags=["applications"])
app.include_router(prepare.router, prefix="/prepare", tags=["prepare"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])


@app.get("/health")
def health():
    return {"status": "ok"}
