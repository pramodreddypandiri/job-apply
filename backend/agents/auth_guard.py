"""Authenticity guard agent — checks tailored resume for hallucinations."""

from backend.llm.client import extract
from loguru import logger

SYSTEM = """
You are an authenticity checker for job application resumes.
Detect any fabricated or significantly embellished content.
"""

PROMPT_TEMPLATE = """
Compare the original resume against the tailored version.
Flag any content in the tailored version that:
1. Claims experience at companies not in the original
2. Claims dates of employment not in the original
3. Claims achievements with numbers significantly higher than original (>50% inflation)
4. Claims skills at professional level that only appear as side projects in original
5. Removes significant gaps or career changes from the original

Return JSON:
{{
  "passes": bool,
  "flags": [
    {{"type": str, "original": str, "proposed": str, "severity": "block"|"warn"}}
  ]
}}

Original: {original}
Tailored: {tailored}
"""


def check_authenticity(original: str, tailored: str) -> dict:
    """Check tailored resume against original for hallucinations."""
    prompt = PROMPT_TEMPLATE.format(original=original, tailored=tailored)
    result = extract(prompt=prompt, system=SYSTEM, max_tokens=1000)

    if not result.get("passes", True):
        block_flags = [f for f in result.get("flags", []) if f.get("severity") == "block"]
        if block_flags:
            logger.warning(f"Auth guard BLOCKED: {len(block_flags)} blocking flags")
        else:
            logger.info(f"Auth guard passed with {len(result.get('flags', []))} warnings")
    else:
        logger.info("Auth guard passed cleanly")

    return result
