"""Narration loader for cascade prompt files.

Prompt files live in prompts/{cascade_name}/{version}.md.
Sections are marked with ## section_key headers.
"""

from __future__ import annotations

import re
from pathlib import Path

# Default prompts directory: project root / prompts
_DEFAULT_PROMPTS_ROOT = Path(__file__).parent.parent.parent.parent / "prompts"

_HEADER_RE = re.compile(r"^## (\w+)\s*$", re.MULTILINE)


def load_narration(
    cascade_name: str,
    version: str = "v1_baseline",
    prompts_root: Path | None = None,
) -> dict[str, str]:
    """Load narration sections from a cascade prompt file.

    Args:
        cascade_name: Subdirectory name under prompts/ (e.g. "swayback").
        version: Filename stem (e.g. "v1_baseline" → "v1_baseline.md").
        prompts_root: Override the default prompts directory (used in tests).

    Returns:
        Dict mapping section key → body text (stripped).

    Raises:
        FileNotFoundError: If the prompt file does not exist, with the
            attempted path in the error message.
    """
    root = prompts_root if prompts_root is not None else _DEFAULT_PROMPTS_ROOT
    prompt_path = root / cascade_name / f"{version}.md"

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path} "
            f"(cascade={cascade_name!r}, version={version!r})"
        )

    text = prompt_path.read_text(encoding="utf-8")

    # Split on section headers
    parts = _HEADER_RE.split(text)
    # parts = [pre_text, key1, body1, key2, body2, ...]
    result: dict[str, str] = {}
    it = iter(parts[1:])  # skip pre-header text
    for key, body in zip(it, it, strict=False):
        result[key] = body.strip()

    return result
