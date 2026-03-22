"""Profile analyser agent — GitHub/portfolio skill extraction."""

import httpx
from backend.llm.client import extract
from backend.config import get_settings
from loguru import logger


def calculate_depth_score(signals: dict) -> int:
    """Calculate skill depth (1-5) from signal scores."""
    score = 0
    if signals.get("ownership_score", 0) > 0.8:
        score += 2
    elif signals.get("ownership_score", 0) > 0.5:
        score += 1
    if signals.get("longevity_days", 0) > 90:
        score += 1
    if signals.get("articulacy_score", 0) > 0.5:
        score += 1
    if signals.get("external_validation", 0) > 10:
        score += 1
    return min(5, max(1, score))


def analyse_github(username: str) -> list[dict]:
    """Analyse GitHub repos and extract skill signals."""
    settings = get_settings()
    headers = {}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"

    logger.info(f"Analysing GitHub profile: {username}")

    response = httpx.get(
        f"https://api.github.com/users/{username}/repos",
        headers=headers,
        params={"sort": "updated", "per_page": 30},
        timeout=30,
    )
    response.raise_for_status()
    repos = response.json()

    skills = []
    seen_langs = set()

    for repo in repos:
        if repo.get("fork"):
            continue

        # Get languages
        lang_url = repo.get("languages_url", "")
        if lang_url:
            try:
                lang_resp = httpx.get(lang_url, headers=headers, timeout=10)
                languages = lang_resp.json() if lang_resp.status_code == 200 else {}
            except Exception:
                languages = {}
        else:
            languages = {}

        # Calculate signals
        signals = {
            "ownership_score": 1.0,  # own repos
            "longevity_days": 0,
            "articulacy_score": min(len(repo.get("description") or "") / 200, 1.0),
            "external_validation": (repo.get("stargazers_count", 0) + repo.get("forks_count", 0)),
        }

        if repo.get("created_at") and repo.get("pushed_at"):
            from datetime import datetime
            created = datetime.fromisoformat(repo["created_at"].rstrip("Z"))
            pushed = datetime.fromisoformat(repo["pushed_at"].rstrip("Z"))
            signals["longevity_days"] = (pushed - created).days

        depth = calculate_depth_score(signals)

        for lang in languages:
            if lang.lower() not in seen_langs:
                seen_langs.add(lang.lower())
                skills.append({
                    "skill_name": lang,
                    "category": "stack",
                    "depth": depth,
                    "source": ["github"],
                    "ownership_level": "author",
                    "interview_defensible": depth >= 3,
                })

    logger.info(f"GitHub analysis complete: {len(skills)} skills extracted from {len(repos)} repos")
    return skills


def analyse_resume(resume_text: str) -> list[dict]:
    """Extract skills from resume text using LLM."""
    logger.info("Analysing resume text for skills")
    try:
        result = extract(
            prompt=(
                "Extract all technical skills, tools, frameworks, and languages from this resume. "
                "For each skill, estimate depth (1-5) based on how prominently it features.\n"
                'Return JSON: {"skills": [{"skill_name": str, "category": "stack"|"cs_fundamentals"|"system_design"|"soft_skills", "depth": int}]}\n\n'
                f"{resume_text[:6000]}"
            ),
            system="You are a technical recruiter extracting skills from a resume. Be thorough but accurate.",
            max_tokens=1000,
        )
        skills = result.get("skills", [])
        return [
            {**s, "depth": min(5, max(1, s.get("depth", 2))), "source": ["resume"], "ownership_level": "self-reported"}
            for s in skills
        ]
    except Exception as e:
        logger.error(f"Resume analysis failed: {e}")
        return []


def analyse_portfolio(url: str) -> list[dict]:
    """Fetch portfolio URL and extract skill mentions."""
    logger.info(f"Analysing portfolio: {url}")
    try:
        response = httpx.get(url, follow_redirects=True, timeout=30)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n", strip=True)[:4000]

        result = extract(
            prompt=f"Extract technical skills and technologies mentioned in this portfolio page. "
                   f"Return JSON: {{\"skills\": [{{\"skill_name\": str, \"category\": \"stack\"|\"cs_fundamentals\"|\"system_design\"}}]}}\n\n{text}",
            system="You are a technical skill extractor. Extract skills from portfolio text.",
            max_tokens=500,
        )

        skills = result.get("skills", [])
        return [
            {**s, "depth": 2, "source": ["portfolio"], "ownership_level": "user"}
            for s in skills
        ]

    except Exception as e:
        logger.error(f"Portfolio analysis failed: {e}")
        return []
