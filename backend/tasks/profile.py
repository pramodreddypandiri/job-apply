"""Profile analysis Celery tasks."""

from backend.tasks.celery_app import celery_app
from loguru import logger


@celery_app.task(bind=True, max_retries=2)
def analyse_profile(self, user_id: str):
    """Run full profile analysis (GitHub + portfolio). Enqueued from /profile/analyse."""
    logger.info(f"[analyse_profile] Starting for user {user_id}")
    try:
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()

        profile = db.get_user_profile(user_id)
        if not profile:
            raise ValueError(f"User {user_id} not found")

        # GitHub analysis
        if profile.get("github_username"):
            from backend.agents.profile_analyser import analyse_github
            github_skills = analyse_github(profile["github_username"])
            for skill in github_skills:
                db.upsert_skill(user_id, skill["skill_name"], {
                    "category": skill.get("category", "stack"),
                    "depth": skill["depth"],
                    "source": skill.get("source", ["github"]),
                    "ownership_level": skill.get("ownership_level", "contributor"),
                })

        # Portfolio analysis
        if profile.get("portfolio_url"):
            from backend.agents.profile_analyser import analyse_portfolio
            portfolio_skills = analyse_portfolio(profile["portfolio_url"])
            for skill in portfolio_skills:
                db.upsert_skill(user_id, skill["skill_name"], {
                    "category": skill.get("category", "stack"),
                    "depth": skill["depth"],
                    "source": skill.get("source", ["portfolio"]),
                })

        logger.info(f"[analyse_profile] Completed for user {user_id}")
        return {"user_id": user_id, "status": "completed"}

    except Exception as exc:
        logger.error(f"[analyse_profile] Failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
