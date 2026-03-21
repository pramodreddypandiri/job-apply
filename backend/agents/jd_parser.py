"""Job description parser agent — extracts structured JD from URL."""

import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from backend.llm.client import extract
from backend.llm.structured import extract_json_block
from loguru import logger

ATS_PATTERNS = {
    "greenhouse.io": "greenhouse",
    "boards.greenhouse.io": "greenhouse",
    "lever.co": "lever",
    "jobs.lever.co": "lever",
    "myworkdayjobs.com": "workday",
    "icims.com": "icims",
    "ashbyhq.com": "ashby",
    "smartrecruiters.com": "smartrecruiters",
    "taleo.net": "taleo",
}

SYSTEM = """
You are a job description parser. Extract structured information from job postings.
Be precise. If a field is not mentioned, use null.
"""

PROMPT_TEMPLATE = """
Parse this job description and return JSON with this exact structure:
{{
  "company_name": str,
  "role_title": str,
  "role_title_normalised": str,
  "seniority": str | null,
  "location": str | null,
  "team": str | null,
  "ats_type": str | null,
  "required_skills": [str],
  "nice_to_have_skills": [str],
  "required_experience_years": int | null,
  "about_company": str,
  "role_summary": str,
  "key_responsibilities": [str],
  "keywords": [str],
  "salary_range": str | null,
  "visa_sponsorship": bool | null
}}

Job description:
{jd_text}
"""


def detect_ats(url: str) -> str | None:
    """Detect ATS type from URL patterns."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    for pattern, ats_type in ATS_PATTERNS.items():
        if pattern in hostname:
            return ats_type
    return None


def fetch_page_text(url: str) -> str:
    """Fetch URL and extract text content."""
    logger.info(f"Fetching page: {url}")
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # Truncate to ~8000 chars for LLM context
    return text[:8000]


def parse_job_description(url: str) -> dict:
    """Full JD parsing pipeline: fetch URL → extract text → parse with LLM."""
    jd_raw = fetch_page_text(url)
    ats_type = detect_ats(url)

    prompt = PROMPT_TEMPLATE.format(jd_text=jd_raw)
    jd_parsed = extract(prompt=prompt, system=SYSTEM, max_tokens=2000)

    # Override ATS type if detected from URL
    if ats_type:
        jd_parsed["ats_type"] = ats_type

    logger.info(f"Parsed JD: {jd_parsed.get('company_name')} — {jd_parsed.get('role_title')}")

    return {
        "jd_raw": jd_raw,
        "jd_parsed": jd_parsed,
        "ats_type": jd_parsed.get("ats_type"),
    }
