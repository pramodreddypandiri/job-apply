from pydantic import BaseModel
from datetime import datetime


class CheckURLRequest(BaseModel):
    url: str


class CheckURLResponse(BaseModel):
    status: str  # "new" | "duplicate" | "processing" | "needs_action" | "applied" | "rejected_reposted"
    canonical_url: str | None = None
    application: dict | None = None
    message: str | None = None


class StartApplicationRequest(BaseModel):
    url: str
    instructions: str | None = None
    referral_context: str | None = None


class StartApplicationResponse(BaseModel):
    application_id: str
    task_id: str
    status: str = "processing"


class ApplicationStatusResponse(BaseModel):
    status: str
    step: str | None = None  # "parsing_jd" | "tailoring" | "review_pending" | "filling_form" | "submitted"
    progress: int = 0


class ApproveRequest(BaseModel):
    resume_text: str | None = None
    cover_letter_text: str | None = None


class ApplicationSummary(BaseModel):
    id: str
    company_name: str
    role_title: str
    status: str
    submitted_at: str | None = None
    updated_at: str | None = None
    jd_overlap_score: float | None = None


class ApplicationListResponse(BaseModel):
    applications: list[ApplicationSummary]
    total: int


class ResumeDiffItem(BaseModel):
    type: str  # "reframed" | "elevated" | "added" | "removed"
    original: str | None = None
    new: str
    reason: str


class ResumeDiffSection(BaseModel):
    section: str
    items: list[ResumeDiffItem]


class ResumeDiffResponse(BaseModel):
    sections: list[ResumeDiffSection]
    pct_changed: float
    skills_added: list[str]
    jd_overlap_score: float


class ErrorResponse(BaseModel):
    error: dict  # {"code": str, "message": str, "details": dict | None}
