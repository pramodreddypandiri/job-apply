"""Pydantic models for structured master resume."""

from pydantic import BaseModel


class PersonalDetails(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""


class Experience(BaseModel):
    company: str = ""
    role: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    current: bool = False
    bullets: list[str] = []


class Education(BaseModel):
    institution: str = ""
    degree: str = ""
    field: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    highlights: list[str] = []


class Project(BaseModel):
    name: str = ""
    description: str = ""
    tech_stack: list[str] = []
    url: str = ""
    bullets: list[str] = []


class SkillCategory(BaseModel):
    category: str = ""
    items: list[str] = []


class Certification(BaseModel):
    name: str = ""
    issuer: str = ""
    date: str = ""
    url: str = ""


class MasterResume(BaseModel):
    personal_details: PersonalDetails = PersonalDetails()
    summary: str = ""
    experience: list[Experience] = []
    education: list[Education] = []
    projects: list[Project] = []
    skills: list[SkillCategory] = []
    certifications: list[Certification] = []


class MasterResumeResponse(MasterResume):
    id: str | None = None
    user_id: str | None = None
