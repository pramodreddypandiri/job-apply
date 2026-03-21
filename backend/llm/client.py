import json
import anthropic
from enum import Enum
from loguru import logger


class Model(str, Enum):
    HAIKU = "claude-haiku-4-5-20251001"
    SONNET = "claude-sonnet-4-5-20250514"


client = anthropic.Anthropic()


def extract(prompt: str, system: str, max_tokens: int = 1000) -> dict:
    """Use Haiku for all extraction/classification. Returns parsed JSON."""
    logger.debug(f"LLM extract call (Haiku) — {len(prompt)} chars")
    response = client.messages.create(
        model=Model.HAIKU,
        max_tokens=max_tokens,
        system=system + "\n\nRespond ONLY with valid JSON. No preamble, no markdown.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    return json.loads(text)


def generate(prompt: str, system: str, max_tokens: int = 4000) -> str:
    """Use Sonnet for all generation tasks. Returns plain text."""
    logger.debug(f"LLM generate call (Sonnet) — {len(prompt)} chars")
    response = client.messages.create(
        model=Model.SONNET,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
