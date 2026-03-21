"""Interview prep generator agent — research + prep plan."""

import json
from backend.llm.client import generate
from backend.llm.structured import extract_json_block
from loguru import logger

PREP_PLAN_SYSTEM = """
You are an expert interview coach. Create a personalised, day-by-day interview prep plan.
Base the plan on:
1. The actual interview process at this company (from research)
2. The user's skill gaps vs what the role requires
3. The specific claims made in the user's tailored resume (they must be able to defend these)
4. The time available before the interview
"""

PREP_PLAN_PROMPT = """
Interview details:
- Company: {company}
- Role: {role}
- Interview type: {interview_type}
- Days available: {days_available}

User's tailored resume claims to defend:
{claims_to_defend}

User's skill gaps for this role:
{gap_topics}

Generate a day-by-day prep plan. Return JSON:
{{
  "interview_type": [str],
  "process_summary": str,
  "question_patterns": [{{"topic": str, "frequency": int, "example_questions": [str]}}],
  "prep_plan": {{
    "days": [{{
      "day": int,
      "focus": str,
      "tasks": [str],
      "resources": [{{"title": str, "url": str}}],
      "time_estimate_mins": int
    }}]
  }},
  "star_stories": [{{
    "theme": str,
    "project": str,
    "situation": str,
    "task": str,
    "action": str,
    "result": str
  }}],
  "gap_topics": [str],
  "strength_topics": [str]
}}
"""


def generate_prep_plan(
    application: dict,
    resume: dict | None = None,
    skill_graph: list[dict] | None = None,
) -> dict:
    """Generate a full interview prep plan."""
    company = application.get("company_name", "Unknown")
    role = application.get("role_title", "Unknown")

    # Extract claims from resume
    claims = []
    if resume:
        text = resume.get("resume_text", "")
        # Simple extraction: lines starting with bullet-like chars
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith(("•", "-", "–", "▪", "*")) and len(line) > 20:
                claims.append(line.lstrip("•-–▪* "))

    # Find skill gaps
    gaps = []
    if skill_graph:
        jd_skills = set()
        jd_parsed = application.get("jd_parsed", {})
        if isinstance(jd_parsed, dict):
            jd_skills = set(jd_parsed.get("required_skills", []) + jd_parsed.get("nice_to_have_skills", []))

        user_strong = {s["skill_name"].lower() for s in skill_graph if s.get("depth", 0) >= 3}
        gaps = [s for s in jd_skills if s.lower() not in user_strong]

    prompt = PREP_PLAN_PROMPT.format(
        company=company,
        role=role,
        interview_type="coding, system_design, behavioural",
        days_available=7,
        claims_to_defend="\n".join(claims[:10]) or "None extracted",
        gap_topics=", ".join(gaps[:10]) or "None identified",
    )

    response = generate(prompt=prompt, system=PREP_PLAN_SYSTEM, max_tokens=4000)

    try:
        result = extract_json_block(response)
    except Exception as e:
        logger.error(f"Failed to parse prep plan: {e}")
        result = {"process_summary": response, "prep_plan": {"days": []}}

    logger.info(f"Generated prep plan for {company} — {role}")
    return result
