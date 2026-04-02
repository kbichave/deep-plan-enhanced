"""Prompt loading utilities for LLM clients."""

import json
from pathlib import Path


def load_prompts(prompt_dir: str) -> tuple[str, str, dict | None]:
    """Load system, user prompts and optional response schema.

    Args:
        prompt_dir: Path to directory containing prompt files

    Returns:
        Tuple of (system_prompt, user_prompt, response_schema)
        response_schema is None if response.json doesn't exist

    Raises:
        FileNotFoundError: If system or user prompt file missing
    """
    prompt_path = Path(prompt_dir)

    system = (prompt_path / "system").read_text()
    user = (prompt_path / "user").read_text()

    response_schema = None
    response_path = prompt_path / "response.json"
    if response_path.exists():
        response_schema = json.loads(response_path.read_text())

    return system, user, response_schema


def format_prompt(template: str, **kwargs) -> str:
    """Format prompt template with provided values.

    Args:
        template: String with {PLACEHOLDER} markers
        **kwargs: Values to substitute for placeholders

    Returns:
        Formatted string with placeholders replaced

    Raises:
        KeyError: If placeholder in template has no corresponding kwarg
    """
    return template.format(**kwargs)
