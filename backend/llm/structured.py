"""JSON mode helpers for structured LLM output."""

import json
import re
from loguru import logger


def extract_json_block(text: str) -> dict:
    """Extract a JSON block from LLM output, handling markdown fences."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try extracting from tagged block (e.g. <changes>...</changes>)
    match = re.search(r"<changes>\s*(.*?)\s*</changes>", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    logger.error(f"Failed to extract JSON from LLM output: {text[:200]}...")
    raise ValueError("Could not extract JSON from LLM response")
