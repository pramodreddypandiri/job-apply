"""Narrative aligner agent — tailors resume to match JD."""

import json
from backend.llm.client import generate
from backend.llm.structured import extract_json_block
from loguru import logger

SYSTEM = """
You are an expert resume writer specialising in ATS optimisation and narrative alignment.
Your goal is to reframe the user's REAL experience to best match the job description.

RULES:
- Never fabricate experience, companies, dates, or achievements
- You may reframe how existing experience is described
- You may elevate side projects from the skill graph if depth >= 3 and interview_defensible = true
- When elevating a side project, frame it as personal/side project — never as professional employment
- Use strong action verbs and quantify where the original already has numbers
- Integrate keywords from the JD naturally — never keyword-stuff
- Keep total resume length appropriate for seniority (1 page junior, 1-2 pages senior+)
"""

PROMPT_TEMPLATE = """
Job Description (parsed):
{jd_parsed}

User's master resume:
{master_resume}

Skill graph entries eligible for elevation (depth >= 3, interview_defensible = true):
{eligible_skills}

Instructions from user:
{user_instructions}

Rewrite the resume to maximise fit for this role. Return the full resume text.
At the end, append a JSON block tagged <changes> with this structure:
{{
  "changes": [
    {{"type": "reframed"|"elevated"|"added"|"removed", "section": str, "original": str|null, "new": str, "reason": str}}
  ],
  "pct_changed": float,
  "skills_elevated": [str],
  "projects_elevated": [str],
  "jd_overlap_score": float
}}
"""


def align_resume(
    jd_parsed: dict,
    master_resume: str,
    skill_graph: list[dict],
    user_instructions: str | None = None,
) -> dict:
    """Generate a tailored resume aligned to the JD."""
    # Filter eligible skills for elevation
    eligible = [
        s for s in skill_graph
        if s.get("depth", 0) >= 3 and s.get("interview_defensible", False)
    ]

    prompt = PROMPT_TEMPLATE.format(
        jd_parsed=json.dumps(jd_parsed, indent=2),
        master_resume=master_resume,
        eligible_skills=json.dumps(eligible, indent=2, default=str),
        user_instructions=user_instructions or "None",
    )

    response = generate(prompt=prompt, system=SYSTEM, max_tokens=4000)

    # Split resume text and changes JSON
    resume_text = response
    changes_data = {}

    if "<changes>" in response:
        parts = response.split("<changes>")
        resume_text = parts[0].strip()
        try:
            changes_data = extract_json_block(parts[1])
        except Exception as e:
            logger.warning(f"Failed to parse changes block: {e}")

    logger.info(f"Resume aligned — {changes_data.get('pct_changed', 0)}% changed")

    return {
        "resume_text": resume_text,
        "resume_html": f"<pre>{resume_text}</pre>",  # TODO: proper HTML template
        "changes": changes_data.get("changes", []),
        "pct_changed": changes_data.get("pct_changed", 0),
        "skills_elevated": changes_data.get("skills_elevated", []),
        "projects_elevated": changes_data.get("projects_elevated", []),
        "jd_overlap_score": changes_data.get("jd_overlap_score", 0),
    }
