"""Jinja2 prompt template loader."""

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

_prompts_dir = Path(__file__).parent / "prompts"
env = Environment(loader=FileSystemLoader(str(_prompts_dir)))


def render_prompt(template_name: str, **kwargs) -> str:
    return env.get_template(f"{template_name}.j2").render(**kwargs)
