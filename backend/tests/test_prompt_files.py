"""Tests for presence and correctness of prompt files.

These tests verify that required prompt files exist and contain no unresolved
{{...}} placeholders (after substitution with the variables they expect).
"""

import re
from pathlib import Path

import pytest

# Repo root — prompts/ directory lives two levels above backend/
_REPO_ROOT = Path(__file__).parent.parent.parent
_PROMPTS_ROOT = _REPO_ROOT / "prompts"


class TestShoulderSleevePromptFile:
    def test_shoulder_sleeve_prompt_file_exists(self) -> None:
        """prompts/diagnosis/shoulder_sleeve/v1_baseline.md exists."""
        prompt_path = _PROMPTS_ROOT / "diagnosis" / "shoulder_sleeve" / "v1_baseline.md"
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

    def test_shoulder_sleeve_prompt_no_unresolved_placeholders(self) -> None:
        """shoulder_sleeve prompt has no unresolved {{...}} placeholders (no variables required)."""
        from lib.diagnosis.prompts import load_prompt, substitute

        template = load_prompt(
            "diagnosis/shoulder_sleeve",
            version="v1_baseline",
            prompts_root=_PROMPTS_ROOT,
        )
        # The shoulder_sleeve prompt takes no variables — substitute with empty dict.
        # substitute() raises KeyError if any {{var}} remains unresolved, so this
        # will fail the test if any placeholder is present.
        rendered = substitute(template, {})

        # Extra explicit check: no {{ }} placeholders remain in the rendered output
        unresolved = re.findall(r"\{\{(\w+)\}\}", rendered)
        assert unresolved == [], f"Unresolved placeholders found: {unresolved}"

    def test_shoulder_sleeve_prompt_contains_region_name(self) -> None:
        """shoulder_sleeve prompt references the region name for self-identification."""
        prompt_path = _PROMPTS_ROOT / "diagnosis" / "shoulder_sleeve" / "v1_baseline.md"
        content = prompt_path.read_text(encoding="utf-8")
        assert "shoulder_sleeve" in content

    def test_shoulder_sleeve_prompt_contains_json_schema_block(self) -> None:
        """shoulder_sleeve prompt contains a ```json code fence with the output schema."""
        prompt_path = _PROMPTS_ROOT / "diagnosis" / "shoulder_sleeve" / "v1_baseline.md"
        content = prompt_path.read_text(encoding="utf-8")
        assert "```json" in content, "Expected a ```json fenced code block in the prompt"


class TestCoordinatorPromptContainsShoulderSleeve:
    def test_coordinator_prompt_contains_shoulder_sleeve_string(self) -> None:
        """The coordinator prompt file references 'shoulder_sleeve'."""
        prompt_path = _PROMPTS_ROOT / "diagnosis" / "coordinator" / "v1_baseline.md"
        content = prompt_path.read_text(encoding="utf-8")
        assert "shoulder_sleeve" in content, (
            "coordinator prompt does not mention 'shoulder_sleeve'; "
            "expected it to be updated per spec 22"
        )

    def test_coordinator_prompt_mentions_four_specialists(self) -> None:
        """Coordinator prompt mentions 'four' specialists (updated from three)."""
        prompt_path = _PROMPTS_ROOT / "diagnosis" / "coordinator" / "v1_baseline.md"
        content = prompt_path.read_text(encoding="utf-8")
        assert "four" in content, (
            "coordinator prompt should say 'four' (or 'up to four') specialists"
        )
