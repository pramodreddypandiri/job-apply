"""Profile routes."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from backend.api.middleware.auth import get_current_user
from backend.db.client import supabase
from backend.db import queries as db
from backend.models.profile import (
    OnboardRequest,
    ProfileResponse,
    SkillGraphResponse,
    SkillEntry,
    SkillDepthUpdate,
)
from loguru import logger

router = APIRouter()


@router.get("", response_model=ProfileResponse)
async def get_profile(user: dict = Depends(get_current_user)):
    profile = db.get_user_profile(user["id"])
    if not profile:
        return ProfileResponse(id=user["id"], onboarded=False)

    skills = db.get_skill_graph(user["id"])
    depths = [s["depth"] for s in skills if s.get("depth")]

    return ProfileResponse(
        id=user["id"],
        full_name=profile.get("full_name"),
        email=profile.get("email"),
        target_roles=profile.get("target_roles"),
        skill_graph_summary={
            "total_skills": len(skills),
            "avg_depth": round(sum(depths) / len(depths), 1) if depths else 0,
            "gaps": [s["skill_name"] for s in skills if s.get("depth", 0) < 3][:5],
            "strengths": [s["skill_name"] for s in skills if s.get("depth", 0) >= 4][:5],
        },
        onboarded=profile.get("onboarded_at") is not None,
    )


@router.post("/onboard")
async def onboard(
    target_roles: str = Form(...),
    target_locations: str = Form(""),
    seniority_floor: str = Form("any"),
    excluded_keywords: str = Form(""),
    linkedin_url: str = Form(""),
    github_username: str = Form(""),
    portfolio_url: str = Form(""),
    resume_pdf: UploadFile = File(None),
    user: dict = Depends(get_current_user),
):
    """Initial onboarding — stores profile, uploads resume, triggers analysis."""
    data = {
        "full_name": user.get("email", "").split("@")[0],
        "email": user.get("email"),
        "target_roles": [r.strip() for r in target_roles.split(",") if r.strip()],
        "target_locations": [l.strip() for l in target_locations.split(",") if l.strip()],
        "seniority_floor": seniority_floor,
        "excluded_keywords": [k.strip() for k in excluded_keywords.split(",") if k.strip()],
        "linkedin_url": linkedin_url or None,
        "github_username": github_username or None,
        "portfolio_url": portfolio_url or None,
        "onboarded_at": datetime.now(timezone.utc).isoformat(),
    }

    # Upload resume PDF to Supabase Storage
    if resume_pdf:
        content = await resume_pdf.read()
        path = f"{user['id']}/master_resume.pdf"
        supabase.storage.from_("resumes").upload(path, content, {"content-type": "application/pdf"})
        data["resume_pdf_url"] = f"{supabase.supabase_url}/storage/v1/object/public/resumes/{path}"

        # Extract text from PDF
        try:
            import fitz  # pymupdf
            doc = fitz.open(stream=content, filetype="pdf")
            data["resume_master"] = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception as e:
            logger.warning(f"PDF text extraction failed: {e}")
            data["resume_master"] = f"[Uploaded: {resume_pdf.filename}]"

    profile = db.upsert_user_profile(user["id"], data)

    # Trigger background profile analysis
    from backend.tasks.profile import analyse_profile
    task = analyse_profile.delay(user["id"])

    return {"status": "onboarded", "task_id": str(task.id)}


@router.post("/analyse")
async def analyse(user: dict = Depends(get_current_user)):
    """Trigger background profile analysis (GitHub + portfolio)."""
    from backend.tasks.profile import analyse_profile
    task = analyse_profile.delay(user["id"])
    return {"task_id": str(task.id), "status": "queued"}


@router.get("/skill-graph", response_model=SkillGraphResponse)
async def get_skill_graph(user: dict = Depends(get_current_user)):
    skills = db.get_skill_graph(user["id"])
    return SkillGraphResponse(
        skills=[
            SkillEntry(
                skill_name=s["skill_name"],
                category=s.get("category"),
                depth=s.get("depth", 1),
                source=s.get("source", []),
                ownership_level=s.get("ownership_level"),
                interview_defensible=s.get("interview_defensible", False),
                star_scaffold=s.get("star_scaffold"),
            )
            for s in skills
        ]
    )


@router.patch("/skill-graph/{skill_name}")
async def update_skill_depth(
    skill_name: str,
    body: SkillDepthUpdate,
    user: dict = Depends(get_current_user),
):
    """User manually adjusts a skill depth."""
    db.upsert_skill(user["id"], skill_name, {"depth": body.depth})
    return {"status": "updated"}
