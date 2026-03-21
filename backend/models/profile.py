from pydantic import BaseModel
from datetime import datetime


class OnboardRequest(BaseModel):
    target_roles: list[str]
    target_locations: list[str] = []
    seniority_floor: str = "any"
    excluded_keywords: list[str] = []
    linkedin_url: str | None = None
    github_username: str | None = None
    portfolio_url: str | None = None


class ProfileResponse(BaseModel):
    id: str
    full_name: str | None = None
    email: str | None = None
    target_roles: list[str] | None = None
    skill_graph_summary: dict | None = None
    onboarded: bool = False


class SkillEntry(BaseModel):
    skill_name: str
    category: str | None = None
    depth: int
    source: list[str] = []
    ownership_level: str | None = None
    interview_defensible: bool = False
    star_scaffold: str | None = None


class SkillGraphResponse(BaseModel):
    skills: list[SkillEntry]


class SkillDepthUpdate(BaseModel):
    depth: int
