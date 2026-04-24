"""Prompt file loading and variable substitution utilities.

All prompts are files in the top-level prompts/ directory — never hardcoded
strings in Python (CLAUDE.md critical rule 3). This module is the single
place that reads those files and substitutes {{var}} placeholders.

Usage:
    template = load_prompt("hello_world")
    rendered = substitute(template, {"name": "Steph"})
"""

import re
from pathlib import Path

# Default root: two levels up from this file (backend/lib/diagnosis/ -> repo root / prompts)
_DEFAULT_PROMPTS_ROOT = Path(__file__).parent.parent.parent.parent / "prompts"


def load_prompt(
    name: str,
    version: str = "v1_baseline",
    prompts_root: Path | None = None,
) -> str:
    """Load a prompt template from the prompts/ directory.

    Args:
        name: Name of the prompt subdirectory (e.g. 'hello_world').
        version: Version filename stem (e.g. 'v1_baseline'). Defaults to 'v1_baseline'.
        prompts_root: Override the root prompts directory (used in tests).

    Returns:
        The raw prompt file contents as a string.

    Raises:
        FileNotFoundError: If the prompt file does not exist. The error message
            includes the attempted path so callers can diagnose misconfiguration.
    """
    root = prompts_root if prompts_root is not None else _DEFAULT_PROMPTS_ROOT
    prompt_path = root / name / f"{version}.md"

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}. "
            f"Expected prompts/{name}/{version}.md to exist."
        )

    return prompt_path.read_text(encoding="utf-8")


def substitute(template: str, variables: dict[str, str]) -> str:
    """Replace {{var}} placeholders in template with values from variables.

    Args:
        template: A prompt string containing zero or more {{var}} placeholders.
        variables: Mapping of placeholder names to replacement values.

    Returns:
        The template with all placeholders replaced.

    Raises:
        KeyError: If the template contains a {{var}} that is not present in
            variables. Never silently passes through unreplaced placeholders.
    """
    pattern = re.compile(r"\{\{(\w+)\}\}")

    # First pass: validate all placeholders are present
    found_keys = pattern.findall(template)
    for key in found_keys:
        if key not in variables:
            raise KeyError(
                f"Prompt template references '{{{{{key}}}}}' but '{key}' "
                f"is not in the provided variables. "
                f"Provided keys: {sorted(variables.keys())}"
            )

    # Second pass: substitute all placeholders
    def replacer(match: re.Match) -> str:  # type: ignore[type-arg]
        return variables[match.group(1)]

    return pattern.sub(replacer, template)
