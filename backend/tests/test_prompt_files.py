"""Tests for presence and correctness of prompt files.

These tests verify that required prompt files exist and contain no unresolved
{{...}} placeholders (after substitution with the variables they expect).
"""

import re
from pathlib import Path

# Repo root — prompts/ directory lives two levels above backend/
_REPO_ROOT = Path(__file__).parent.parent.parent
_PROMPTS_ROOT = _REPO_ROOT / "prompts"


class TestNeckCollarPromptFile:
    def test_neck_collar_prompt_file_exists(self) -> None:
        """prompts/diagnosis/neck_collar/v1_baseline.md exists."""
        prompt_path = _PROMPTS_ROOT / "diagnosis" / "neck_collar" / "v1_baseline.md"
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

    def test_neck_collar_prompt_no_unresolved_placeholders(self) -> None:
        """neck_collar prompt has no unresolved {{...}} placeholders (no variables required)."""
        from lib.diagnosis.prompts import load_prompt, substitute

        template = load_prompt(
            "diagnosis/neck_collar",
            version="v1_baseline",
            prompts_root=_PROMPTS_ROOT,
        )
        # The neck_collar prompt takes no variables — substitute with empty dict.
        rendered = substitute(template, {})

        # Extra explicit check: no {{ }} placeholders remain in the rendered output
        unresolved = re.findall(r"\{\{(\w+)\}\}", rendered)
        assert unresolved == [], f"Unresolved placeholders found: {unresolved}"

    def test_neck_collar_prompt_contains_json_schema_block(self) -> None:
        """neck_collar prompt contains a ```json code fence with the output schema."""
        prompt_path = _PROMPTS_ROOT / "diagnosis" / "neck_collar" / "v1_baseline.md"
        content = prompt_path.read_text(encoding="utf-8")
        assert "```json" in content, "Expected a ```json fenced code block in the prompt"


class TestCoordinatorPromptContainsNeckCollar:
    def test_coordinator_prompt_contains_neck_collar_string(self) -> None:
        """The coordinator prompt file references 'neck_collar'."""
        prompt_path = _PROMPTS_ROOT / "diagnosis" / "coordinator" / "v1_baseline.md"
        content = prompt_path.read_text(encoding="utf-8")
        assert "neck_collar" in content, (
            "coordinator prompt does not mention 'neck_collar'; "
            "expected it to be updated per spec 24"
        )
