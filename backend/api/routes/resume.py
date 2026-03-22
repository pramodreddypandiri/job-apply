"""Master resume routes — structured, editable resume builder."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from backend.api.middleware.auth import get_current_user
from backend.db import queries as db
from backend.models.resume import MasterResume, MasterResumeResponse
from loguru import logger

router = APIRouter()


@router.get("", response_model=MasterResumeResponse)
async def get_resume(user: dict = Depends(get_current_user)):
    """Get the user's master resume. Returns empty structure if none exists."""
    row = db.get_master_resume(user["id"])
    if not row:
        return MasterResumeResponse(user_id=user["id"])
    return MasterResumeResponse(
        id=row.get("id"),
        user_id=row["user_id"],
        personal_details=row.get("personal_details", {}),
        summary=row.get("summary", ""),
        experience=row.get("experience", []),
        education=row.get("education", []),
        projects=row.get("projects", []),
        skills=row.get("skills", []),
        certifications=row.get("certifications", []),
    )


@router.put("", response_model=MasterResumeResponse)
async def save_resume(body: MasterResume, user: dict = Depends(get_current_user)):
    """Save/update the entire master resume."""
    # Ensure users_profile row exists
    if not db.get_user_profile(user["id"]):
        db.upsert_user_profile(user["id"], {"email": user.get("email")})

    data = {
        "personal_details": body.personal_details.model_dump(),
        "summary": body.summary,
        "experience": [e.model_dump() for e in body.experience],
        "education": [e.model_dump() for e in body.education],
        "projects": [p.model_dump() for p in body.projects],
        "skills": [s.model_dump() for s in body.skills],
        "certifications": [c.model_dump() for c in body.certifications],
    }
    row = db.upsert_master_resume(user["id"], data)
    return MasterResumeResponse(
        id=row.get("id"),
        user_id=row["user_id"],
        personal_details=row.get("personal_details", {}),
        summary=row.get("summary", ""),
        experience=row.get("experience", []),
        education=row.get("education", []),
        projects=row.get("projects", []),
        skills=row.get("skills", []),
        certifications=row.get("certifications", []),
    )


@router.post("/upload")
async def upload_and_parse(
    resume_pdf: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a PDF resume, extract text, parse into structured sections via LLM, and save."""
    if not resume_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = await resume_pdf.read()

    # Extract text from PDF
    try:
        import fitz
        doc = fitz.open(stream=content, filetype="pdf")
        resume_text = "\n".join(page.get_text() for page in doc)
        doc.close()
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise HTTPException(status_code=400, detail="Could not read PDF file")

    if not resume_text.strip():
        raise HTTPException(status_code=400, detail="PDF appears to be empty or image-only")

    # Parse with LLM
    try:
        from jinja2 import Environment, FileSystemLoader
        import os

        env = Environment(loader=FileSystemLoader(
            os.path.join(os.path.dirname(__file__), "../../llm/prompts")
        ))
        template = env.get_template("resume_parser.j2")
        prompt = template.render(resume_text=resume_text[:8000])

        from backend.llm.client import extract
        parsed = extract(
            prompt=prompt,
            system="You are a resume parser. Extract structured data from resume text. Be precise and thorough.",
            max_tokens=4000,
        )
    except Exception as e:
        logger.error(f"LLM resume parsing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse resume content")

    # Ensure users_profile row exists (FK requirement for master_resume)
    if not db.get_user_profile(user["id"]):
        db.upsert_user_profile(user["id"], {"email": user.get("email")})

    # Save to DB
    data = {
        "personal_details": parsed.get("personal_details", {}),
        "summary": parsed.get("summary", ""),
        "experience": parsed.get("experience", []),
        "education": parsed.get("education", []),
        "projects": parsed.get("projects", []),
        "skills": parsed.get("skills", []),
        "certifications": parsed.get("certifications", []),
    }
    row = db.upsert_master_resume(user["id"], data)

    # Also update resume_master text in users_profile for backward compat
    db.upsert_user_profile(user["id"], {"resume_master": resume_text})

    return {
        "status": "parsed",
        "resume": MasterResumeResponse(
            id=row.get("id"),
            user_id=row["user_id"],
            **data,
        ).model_dump(),
    }
