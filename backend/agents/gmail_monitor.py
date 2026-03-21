"""Gmail monitor agent — polls and classifies job-related emails."""

from backend.llm.client import extract
from loguru import logger

EMAIL_CLASSIFIER_SYSTEM = """
Classify this email in the context of a job application.
Return JSON only.
"""

EMAIL_CLASSIFIER_PROMPT = """
Email subject: {subject}
Email from: {sender}
Email body (first 500 chars): {body_snippet}

Known applications (company names and roles): {applications_context}

Classify and return:
{{
  "classification": "confirmed"|"viewed"|"interview_invite"|"rejection"|"offer"|"unrelated",
  "company_name": str | null,
  "role_title": str | null,
  "confidence": float,
  "interview_date": str | null,
  "interview_type_hints": [str],
  "action_required": bool,
  "summary": str
}}
"""


def fetch_and_classify_emails(user_id: str) -> list[dict]:
    """Fetch unread emails and classify them."""
    # TODO: Implement Gmail API client
    # For now, return empty list — Gmail integration requires OAuth tokens
    logger.info(f"[gmail_monitor] Polling for user {user_id} — Gmail API not yet connected")
    return []


def classify_email(
    subject: str,
    sender: str,
    body_snippet: str,
    applications_context: str,
) -> dict:
    """Classify a single email using Haiku."""
    prompt = EMAIL_CLASSIFIER_PROMPT.format(
        subject=subject,
        sender=sender,
        body_snippet=body_snippet[:500],
        applications_context=applications_context,
    )

    result = extract(prompt=prompt, system=EMAIL_CLASSIFIER_SYSTEM, max_tokens=500)
    logger.info(f"Email classified: {result.get('classification')} — {result.get('summary', '')}")
    return result
