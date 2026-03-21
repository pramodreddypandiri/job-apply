from celery import Celery
from celery.schedules import crontab
from backend.config import get_settings

settings = get_settings()

celery_app = Celery(
    "job_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "backend.tasks.application",
        "backend.tasks.gmail",
        "backend.tasks.profile",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
    result_expires=3600,
)

# Beat schedule — Gmail polling every 5 minutes
celery_app.conf.beat_schedule = {
    "poll-gmail-every-5-min": {
        "task": "backend.tasks.gmail.poll_gmail",
        "schedule": crontab(minute="*/5"),
    },
}
