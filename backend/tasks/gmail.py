"""Gmail polling Celery tasks."""

from backend.tasks.celery_app import celery_app
from loguru import logger


@celery_app.task
def poll_gmail():
    """Poll Gmail for all connected users. Runs via Celery Beat every 5 minutes."""
    logger.info("[poll_gmail] Starting Gmail poll cycle")
    try:
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()

        # Get all users with Gmail connected
        from backend.db.client import supabase
        result = supabase.table("users_profile").select("id").eq("gmail_connected", True).execute()
        users = result.data

        for user in users:
            try:
                poll_user_gmail.delay(user["id"])
            except Exception as e:
                logger.error(f"[poll_gmail] Failed to enqueue for user {user['id']}: {e}")

    except Exception as exc:
        logger.error(f"[poll_gmail] Failed: {exc}")


@celery_app.task(bind=True, max_retries=1)
def poll_user_gmail(self, user_id: str):
    """Poll Gmail for a single user and classify new emails."""
    logger.info(f"[poll_user_gmail] Polling for user {user_id}")
    try:
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()

        from backend.agents.gmail_monitor import fetch_and_classify_emails
        results = fetch_and_classify_emails(user_id)

        for result in results:
            if result["classification"] == "unrelated":
                continue

            # Find matching application
            apps = db.get_user_applications(user_id)
            matched_app = None
            for app in apps:
                if (result.get("company_name", "").lower() in app.get("company_name", "").lower()
                        or app.get("company_name", "").lower() in result.get("company_name", "").lower()):
                    matched_app = app
                    break

            if not matched_app:
                logger.warning(f"[poll_user_gmail] No matching app for email from {result.get('company_name')}")
                continue

            # Update application status
            status_map = {
                "confirmed": "applied",
                "viewed": "viewed",
                "interview_invite": "interview",
                "rejection": "rejected",
                "offer": "offer",
            }
            new_status = status_map.get(result["classification"])
            if new_status:
                db.update_application(matched_app["id"], {"status": new_status})

            # Create tracker event
            db.create_tracker_event({
                "application_id": matched_app["id"],
                "user_id": user_id,
                "event_type": f"email_{result['classification']}",
                "source": "gmail",
                "email_subject": result.get("subject"),
                "email_snippet": result.get("snippet"),
                "metadata": result,
            })

            # Trigger interview prep if interview invite
            if result["classification"] == "interview_invite":
                trigger_interview_prep.delay(matched_app["id"])

    except Exception as exc:
        logger.error(f"[poll_user_gmail] Failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@celery_app.task
def trigger_interview_prep(application_id: str):
    """Generate interview prep plan after detecting an invite."""
    logger.info(f"[trigger_interview_prep] Starting for application {application_id}")
    try:
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()

        app = db.get_application(application_id)
        resume = db.get_resume_by_application(application_id)
        skills = db.get_skill_graph(app["user_id"])

        from backend.agents.interview_prep import generate_prep_plan
        result = generate_prep_plan(
            application=app,
            resume=resume,
            skill_graph=skills,
        )

        db.create_interview_prep({
            "application_id": application_id,
            "user_id": app["user_id"],
            **result,
        })

        db.create_tracker_event({
            "application_id": application_id,
            "user_id": app["user_id"],
            "event_type": "prep_plan_generated",
            "source": "agent",
        })

    except Exception as exc:
        logger.error(f"[trigger_interview_prep] Failed: {exc}")
