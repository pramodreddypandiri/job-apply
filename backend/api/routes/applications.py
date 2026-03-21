"""Application routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from backend.api.middleware.auth import get_current_user
from backend.db import queries as db
from backend.models.application import (
    CheckURLRequest,
    CheckURLResponse,
    StartApplicationRequest,
    StartApplicationResponse,
    ApplicationStatusResponse,
    ApproveRequest,
    ApplicationListResponse,
    ApplicationSummary,
    ResumeDiffResponse,
)
from loguru import logger

router = APIRouter()


@router.post("/check", response_model=CheckURLResponse)
async def check_url(body: CheckURLRequest, user: dict = Depends(get_current_user)):
    """Deduplication check before starting an application."""
    from backend.agents.deduplicator import normalise_url, build_fingerprint

    canonical = normalise_url(body.url)

    # Check exact URL match
    existing = db.find_application_by_url(user["id"], canonical)
    if existing:
        return CheckURLResponse(
            status="duplicate",
            canonical_url=canonical,
            application=existing,
            message=f"You already applied to {existing.get('company_name', 'this role')}. Status: {existing['status']}.",
        )

    return CheckURLResponse(status="new", canonical_url=canonical)


@router.post("/start", response_model=StartApplicationResponse)
async def start_application(body: StartApplicationRequest, user: dict = Depends(get_current_user)):
    """Start the full application pipeline."""
    from backend.agents.deduplicator import normalise_url

    canonical = normalise_url(body.url)

    # Create application record
    application = db.create_application({
        "user_id": user["id"],
        "source_url": body.url,
        "canonical_url": canonical,
        "company_name": "Detecting...",
        "role_title": "Detecting...",
        "instructions": body.instructions,
        "referral_context": body.referral_context,
        "status": "processing",
    })

    # Start Celery pipeline
    from backend.tasks.application import start_application_pipeline
    result = start_application_pipeline(application["id"])

    return StartApplicationResponse(
        application_id=application["id"],
        task_id=str(result.id),
        status="processing",
    )


@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    status: str | None = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    apps = db.get_user_applications(user["id"], status=status, limit=limit, offset=offset)
    return ApplicationListResponse(
        applications=[
            ApplicationSummary(
                id=a["id"],
                company_name=a.get("company_name", ""),
                role_title=a.get("role_title", ""),
                status=a["status"],
                submitted_at=a.get("submitted_at"),
                updated_at=a.get("updated_at"),
                jd_overlap_score=a.get("jd_overlap_score"),
            )
            for a in apps
        ],
        total=len(apps),
    )


@router.get("/{application_id}")
async def get_application(application_id: str, user: dict = Depends(get_current_user)):
    app = db.get_application(application_id)
    if not app or app["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Application not found")

    resume = db.get_resume_by_application(application_id)
    events = db.get_application_events(application_id)

    return {"application": app, "resume": resume, "events": events}


@router.get("/{application_id}/status", response_model=ApplicationStatusResponse)
async def get_application_status(application_id: str, user: dict = Depends(get_current_user)):
    app = db.get_application(application_id)
    if not app or app["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Application not found")

    step_map = {
        "processing": "parsing_jd",
        "review_pending": "review_pending",
        "applied": "submitted",
        "needs_action": "needs_action",
    }
    progress_map = {
        "processing": 25,
        "review_pending": 75,
        "applied": 100,
        "needs_action": 0,
    }

    return ApplicationStatusResponse(
        status=app["status"],
        step=step_map.get(app["status"], app["status"]),
        progress=progress_map.get(app["status"], 50),
    )


@router.post("/{application_id}/approve")
async def approve_application(
    application_id: str,
    body: ApproveRequest | None = None,
    user: dict = Depends(get_current_user),
):
    """User approves tailored resume. Triggers form fill."""
    app = db.get_application(application_id)
    if not app or app["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Application not found")

    resume = db.get_resume_by_application(application_id)
    if not resume:
        raise HTTPException(status_code=400, detail="No resume found for this application")

    # Apply user edits if any
    updates = {"status": "approved", "approved_at": "now()"}
    if body and body.resume_text:
        updates["resume_text"] = body.resume_text
    if body and body.cover_letter_text:
        updates["cover_letter_text"] = body.cover_letter_text

    db.update_resume(resume["id"], updates)

    # Trigger form fill
    from backend.tasks.application import fill_form
    task = fill_form.delay(application_id)

    return {"status": "approved", "task_id": str(task.id)}


@router.post("/{application_id}/discard")
async def discard_application(application_id: str, user: dict = Depends(get_current_user)):
    app = db.get_application(application_id)
    if not app or app["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Application not found")

    db.update_application(application_id, {"status": "withdrawn"})
    return {"status": "withdrawn"}


@router.get("/{application_id}/resume/diff", response_model=ResumeDiffResponse)
async def get_resume_diff(application_id: str, user: dict = Depends(get_current_user)):
    app = db.get_application(application_id)
    if not app or app["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Application not found")

    resume = db.get_resume_by_application(application_id)
    if not resume:
        raise HTTPException(status_code=400, detail="No resume found")

    changes = resume.get("changes_summary", [])
    sections: dict[str, list] = {}
    for change in changes:
        section = change.get("section", "general")
        sections.setdefault(section, []).append(change)

    return ResumeDiffResponse(
        sections=[
            {"section": sec, "items": items}
            for sec, items in sections.items()
        ],
        pct_changed=resume.get("pct_changed", 0),
        skills_added=resume.get("skills_elevated", []),
        jd_overlap_score=app.get("jd_overlap_score", 0),
    )


@router.get("/{application_id}/prep")
async def get_interview_prep(application_id: str, user: dict = Depends(get_current_user)):
    app = db.get_application(application_id)
    if not app or app["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Application not found")

    prep = db.get_interview_prep(application_id)
    if not prep:
        raise HTTPException(status_code=404, detail="No prep plan found. Waiting for interview invite detection.")

    return prep
