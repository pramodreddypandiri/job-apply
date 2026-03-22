"""Profile analysis Celery tasks."""

from backend.tasks.celery_app import celery_app
from loguru import logger


def _merge_skills(all_skills: list[dict]) -> dict[str, dict]:
    """Deduplicate skills by name, merge sources, keep highest depth."""
    merged: dict[str, dict] = {}
    for skill in all_skills:
        name = skill["skill_name"].lower()
        if name in merged:
            existing = merged[name]
            existing["depth"] = max(existing["depth"], skill["depth"])
            for src in skill.get("source", []):
                if src not in existing["source"]:
                    existing["source"].append(src)
        else:
            merged[name] = {**skill, "skill_name": skill["skill_name"]}
    return merged


@celery_app.task(bind=True, max_retries=2)
def analyse_profile(self, user_id: str):
    """Run full profile analysis (resume + GitHub + portfolio). Enqueued from /profile/analyse."""
    logger.info(f"[analyse_profile] Starting for user {user_id}")
    try:
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()

        profile = db.get_user_profile(user_id)
        if not profile:
            raise ValueError(f"User {user_id} not found")

        all_skills = []

        # Resume analysis
        if profile.get("resume_master") and not profile["resume_master"].startswith("[Uploaded"):
            from backend.agents.profile_analyser import analyse_resume
            all_skills.extend(analyse_resume(profile["resume_master"]))

        # GitHub analysis
        if profile.get("github_username"):
            from backend.agents.profile_analyser import analyse_github
            all_skills.extend(analyse_github(profile["github_username"]))

        # Portfolio analysis
        if profile.get("portfolio_url"):
            from backend.agents.profile_analyser import analyse_portfolio
            all_skills.extend(analyse_portfolio(profile["portfolio_url"]))

        # Merge and upsert
        for skill in _merge_skills(all_skills).values():
            db.upsert_skill(user_id, skill["skill_name"], {
                "category": skill.get("category", "stack"),
                "depth": skill["depth"],
                "source": skill.get("source", []),
                "ownership_level": skill.get("ownership_level", "contributor"),
            })

        logger.info(f"[analyse_profile] Completed for user {user_id}")
        return {"user_id": user_id, "status": "completed"}

    except Exception as exc:
        logger.error(f"[analyse_profile] Failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
