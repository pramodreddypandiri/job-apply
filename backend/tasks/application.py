"""Application pipeline Celery tasks."""

from celery import chain
from backend.tasks.celery_app import celery_app
from loguru import logger


def start_application_pipeline(application_id: str):
    """Full pipeline as a Celery chain."""
    return chain(
        parse_jd.s(application_id),
        align_narrative.s(),
        run_auth_guard.s(),
        generate_resume_pdf.s(),
    ).apply_async()


@celery_app.task(bind=True, max_retries=2)
def parse_jd(self, application_id: str):
    """Fetch URL, extract text, call JD parser agent."""
    logger.info(f"[parse_jd] Starting for application {application_id}")
    try:
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()

        app = db.get_application(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")

        db.update_application(application_id, {"status": "processing"})

        from backend.agents.jd_parser import parse_job_description
        result = parse_job_description(app["source_url"])

        db.update_application(application_id, {
            "jd_raw": result.get("jd_raw", ""),
            "jd_parsed": result.get("jd_parsed", {}),
            "company_name": result["jd_parsed"].get("company_name", app.get("company_name", "")),
            "role_title": result["jd_parsed"].get("role_title", app.get("role_title", "")),
            "ats_type": result.get("ats_type"),
        })

        return {"application_id": application_id, "jd_parsed": result["jd_parsed"]}

    except Exception as exc:
        logger.error(f"[parse_jd] Failed: {exc}")
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()
        db.update_application(application_id, {"status": "needs_action"})
        db.create_tracker_event({
            "application_id": application_id,
            "user_id": app["user_id"] if "app" in dir() else None,
            "event_type": "needs_action",
            "source": "agent",
            "metadata": {"error": str(exc), "step": "parse_jd"},
        })
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=1)
def align_narrative(self, prev_result: dict):
    """Generate tailored resume using narrative aligner."""
    application_id = prev_result["application_id"]
    logger.info(f"[align_narrative] Starting for application {application_id}")
    try:
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()

        app = db.get_application(application_id)
        profile = db.get_user_profile(app["user_id"])
        skills = db.get_skill_graph(app["user_id"])

        # Use structured master resume if available, fall back to plain text
        master_resume_row = db.get_master_resume(app["user_id"])
        if master_resume_row and master_resume_row.get("summary"):
            import json
            # Build a rich text representation from the structured resume
            mr = master_resume_row
            parts = []
            pd = mr.get("personal_details", {})
            if pd.get("full_name"):
                parts.append(pd["full_name"])
                contact = " | ".join(filter(None, [pd.get("email"), pd.get("phone"), pd.get("location")]))
                if contact:
                    parts.append(contact)
            if mr.get("summary"):
                parts.append(f"\nSUMMARY\n{mr['summary']}")
            for exp in mr.get("experience", []):
                dates = f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}"
                parts.append(f"\n{exp.get('role', '')} | {exp.get('company', '')} | {dates}")
                for b in exp.get("bullets", []):
                    parts.append(f"  - {b}")
            for edu in mr.get("education", []):
                parts.append(f"\n{edu.get('degree', '')} {edu.get('field', '')} | {edu.get('institution', '')}")
            for proj in mr.get("projects", []):
                parts.append(f"\n{proj.get('name', '')} — {proj.get('description', '')}")
                for b in proj.get("bullets", []):
                    parts.append(f"  - {b}")
            if mr.get("skills"):
                parts.append("\nSKILLS")
                for sg in mr["skills"]:
                    parts.append(f"{sg.get('category', '')}: {', '.join(sg.get('items', []))}")
            master_resume_text = "\n".join(parts)
        else:
            master_resume_text = profile.get("resume_master", "") if profile else ""

        from backend.agents.narrative import align_resume
        result = align_resume(
            jd_parsed=prev_result["jd_parsed"],
            master_resume=master_resume_text,
            skill_graph=skills,
            user_instructions=app.get("instructions"),
        )

        resume = db.create_resume({
            "application_id": application_id,
            "user_id": app["user_id"],
            "resume_text": result["resume_text"],
            "resume_html": result.get("resume_html", ""),
            "changes_summary": result.get("changes", []),
            "pct_changed": result.get("pct_changed", 0),
            "skills_elevated": result.get("skills_elevated", []),
            "projects_elevated": result.get("projects_elevated", []),
            "status": "draft",
        })

        # Persist JD overlap score on the application
        db.update_application(application_id, {
            "jd_overlap_score": result.get("jd_overlap_score", 0),
        })

        return {
            "application_id": application_id,
            "resume_id": resume["id"],
            "resume_text": result["resume_text"],
        }

    except Exception as exc:
        logger.error(f"[align_narrative] Failed: {exc}")
        try:
            from backend.db.client import init_supabase
            from backend.db import queries as db
            init_supabase()
            db.update_application(application_id, {"status": "needs_action"})
            db.create_tracker_event({
                "application_id": application_id,
                "user_id": app["user_id"] if "app" in dir() else None,
                "event_type": "needs_action",
                "source": "agent",
                "metadata": {"error": str(exc), "step": "align_narrative"},
            })
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=1)
def run_auth_guard(self, prev_result: dict):
    """Check tailored resume for hallucinations."""
    application_id = prev_result["application_id"]
    logger.info(f"[run_auth_guard] Starting for application {application_id}")
    try:
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()

        app = db.get_application(application_id)
        profile = db.get_user_profile(app["user_id"])

        # Use resume_master text or build from structured resume
        original_text = profile.get("resume_master", "") if profile else ""
        if not original_text:
            mr = db.get_master_resume(app["user_id"])
            if mr and mr.get("summary"):
                original_text = mr.get("summary", "")

        from backend.agents.auth_guard import check_authenticity
        result = check_authenticity(
            original=original_text,
            tailored=prev_result["resume_text"],
        )

        if not result["passes"]:
            db.update_resume(prev_result["resume_id"], {"status": "flagged"})
            db.update_application(application_id, {"status": "needs_action"})
            logger.warning(f"[run_auth_guard] Flagged: {result['flags']}")

        return {**prev_result, "auth_guard": result}

    except Exception as exc:
        logger.error(f"[run_auth_guard] Failed: {exc}")
        try:
            from backend.db.client import init_supabase
            from backend.db import queries as db
            init_supabase()
            db.update_application(application_id, {"status": "needs_action"})
            db.create_tracker_event({
                "application_id": application_id,
                "user_id": prev_result.get("user_id"),
                "event_type": "needs_action",
                "source": "agent",
                "metadata": {"error": str(exc), "step": "auth_guard"},
            })
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=1)
def generate_resume_pdf(self, prev_result: dict):
    """Generate PDF from resume HTML and upload to storage."""
    application_id = prev_result["application_id"]
    logger.info(f"[generate_resume_pdf] Starting for application {application_id}")
    try:
        from backend.db.client import init_supabase, supabase
        from backend.db import queries as db
        from backend.config import get_settings
        init_supabase()

        resume = db.get_resume_by_application(application_id)
        if not resume:
            raise ValueError("Resume not found")

        from backend.utils.pdf import generate_resume_pdf as make_pdf
        pdf_bytes = make_pdf(resume.get("resume_html", resume.get("resume_text", "")))

        # Upload to Supabase Storage
        path = f"{resume['user_id']}/{application_id}/resume.pdf"
        bucket = supabase.storage.from_("resumes")
        try:
            bucket.upload(path, pdf_bytes, {"content-type": "application/pdf"})
        except Exception as upload_err:
            # If file exists already, update it
            if "Duplicate" in str(upload_err) or "already exists" in str(upload_err):
                bucket.update(path, pdf_bytes, {"content-type": "application/pdf"})
            else:
                raise

        # Generate a signed URL (works even if bucket is not public)
        signed = bucket.create_signed_url(path, 60 * 60 * 24 * 365)  # 1 year
        pdf_url = signed.get("signedURL") or signed.get("signedUrl", "")

        if not pdf_url:
            # Fallback to public URL
            base_url = get_settings().supabase_url.rstrip("/")
            pdf_url = f"{base_url}/storage/v1/object/public/resumes/{path}"

        db.update_resume(resume["id"], {"resume_pdf_url": pdf_url})
        db.update_application(application_id, {"status": "review_pending"})

        return {"application_id": application_id, "resume_id": resume["id"], "pdf_url": pdf_url}

    except Exception as exc:
        logger.error(f"[generate_resume_pdf] Failed: {exc}")
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=3)
def fill_form(self, application_id: str):
    """Playwright form fill — triggered after user approval."""
    logger.info(f"[fill_form] Starting for application {application_id}")
    try:
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()

        app = db.get_application(application_id)
        resume = db.get_resume_by_application(application_id)
        profile = db.get_user_profile(app["user_id"])

        import asyncio
        from backend.agents.form_fill import fill_application_form
        result = asyncio.run(fill_application_form(
            application_id=application_id,
            apply_url=app.get("apply_url") or app["source_url"],
            resume=resume,
            profile=profile,
        ))

        if result.get("submitted"):
            db.update_application(application_id, {
                "status": "applied",
                "submitted_at": "now()",
                "submission_screenshot_url": result.get("screenshot_url"),
                "form_fill_log": result.get("log", {}),
            })
            db.create_tracker_event({
                "application_id": application_id,
                "user_id": app["user_id"],
                "event_type": "applied",
                "source": "agent",
                "metadata": {"ats_type": app.get("ats_type")},
            })
        else:
            # Form fill didn't submit — escalation or missing button
            db.update_application(application_id, {
                "status": "needs_action",
                "submission_screenshot_url": result.get("screenshot_url"),
                "form_fill_log": result.get("log", {}),
            })
            db.create_tracker_event({
                "application_id": application_id,
                "user_id": app["user_id"],
                "event_type": "needs_action",
                "source": "agent",
                "metadata": {
                    "reason": result.get("escalation") or result.get("log", {}).get("reason", "unknown"),
                    "step": "fill_form",
                },
            })

        return {"application_id": application_id, "submitted": result.get("submitted", False)}

    except Exception as exc:
        logger.error(f"[fill_form] Failed: {exc}")
        from backend.db.client import init_supabase
        from backend.db import queries as db
        init_supabase()
        db.update_application(application_id, {"status": "needs_action"})
        db.create_tracker_event({
            "application_id": application_id,
            "user_id": app["user_id"] if "app" in dir() else None,
            "event_type": "needs_action",
            "source": "agent",
            "metadata": {"error": str(exc), "step": "fill_form"},
        })
        raise self.retry(exc=exc, countdown=60)
