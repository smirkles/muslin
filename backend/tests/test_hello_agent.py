"""Tests for backend/lib/diagnosis/ — prompts, agent, and import hygiene.

Tests are written before implementation (TDD). All non-integration tests
must pass without an Anthropic API key.
"""

import ast
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DIAGNOSIS_PKG = Path(__file__).parent.parent / "lib" / "diagnosis"
PROMPTS_ROOT = Path(__file__).parent.parent.parent / "prompts"


# ---------------------------------------------------------------------------
# prompts.py — load_prompt
# ---------------------------------------------------------------------------


class TestLoadPrompt:
    def test_load_prompt_returns_file_contents(self, tmp_path: Path) -> None:
        """load_prompt returns the exact contents of the prompt file."""
        prompt_dir = tmp_path / "hello_world"
        prompt_dir.mkdir()
        prompt_file = prompt_dir / "v1_baseline.md"
        prompt_file.write_text("Hello {{name}}!")

        from lib.diagnosis.prompts import load_prompt

        result = load_prompt("hello_world", version="v1_baseline", prompts_root=tmp_path)
        assert result == "Hello {{name}}!"

    def test_load_prompt_default_version_is_v1_baseline(self, tmp_path: Path) -> None:
        """load_prompt uses v1_baseline as the default version."""
        prompt_dir = tmp_path / "hello_world"
        prompt_dir.mkdir()
        (prompt_dir / "v1_baseline.md").write_text("Default version content")

        from lib.diagnosis.prompts import load_prompt

        result = load_prompt("hello_world", prompts_root=tmp_path)
        assert result == "Default version content"

    def test_load_prompt_missing_file_raises_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """load_prompt raises FileNotFoundError when prompt file does not exist."""
        from lib.diagnosis.prompts import load_prompt

        with pytest.raises(FileNotFoundError) as exc_info:
            load_prompt("hello_world", version="v1_baseline", prompts_root=tmp_path)

        # The error message must include the attempted path
        assert "hello_world" in str(exc_info.value)

    def test_load_prompt_missing_file_error_includes_path(
        self, tmp_path: Path
    ) -> None:
        """FileNotFoundError message includes the attempted path."""
        from lib.diagnosis.prompts import load_prompt

        with pytest.raises(FileNotFoundError) as exc_info:
            load_prompt("nonexistent_prompt", version="v2", prompts_root=tmp_path)

        error_msg = str(exc_info.value)
        assert "nonexistent_prompt" in error_msg
        assert "v2" in error_msg


# ---------------------------------------------------------------------------
# prompts.py — substitute
# ---------------------------------------------------------------------------


class TestSubstitute:
    def test_substitute_replaces_placeholder(self) -> None:
        """substitute replaces {{name}} with the provided value."""
        from lib.diagnosis.prompts import substitute

        result = substitute("Hello {{name}}!", {"name": "Steph"})
        assert result == "Hello Steph!"

    def test_substitute_replaces_multiple_occurrences(self) -> None:
        """substitute replaces all occurrences of the same placeholder."""
        from lib.diagnosis.prompts import substitute

        result = substitute("{{name}} is great. Hello {{name}}.", {"name": "Steph"})
        assert result == "Steph is great. Hello Steph."

    def test_substitute_replaces_multiple_different_vars(self) -> None:
        """substitute handles multiple distinct variables."""
        from lib.diagnosis.prompts import substitute

        result = substitute("{{greeting}}, {{name}}!", {"greeting": "Hello", "name": "Steph"})
        assert result == "Hello, Steph!"

    def test_substitute_no_placeholders_unchanged(self) -> None:
        """substitute with no placeholders returns the template unchanged."""
        from lib.diagnosis.prompts import substitute

        result = substitute("No placeholders here.", {})
        assert result == "No placeholders here."

    def test_substitute_missing_key_raises_key_error(self) -> None:
        """substitute raises KeyError when a {{var}} in template is missing from variables."""
        from lib.diagnosis.prompts import substitute

        with pytest.raises(KeyError):
            substitute("Hello {{name}}!", {"other": "value"})

    def test_substitute_no_silent_passthrough(self) -> None:
        """substitute never silently passes through unreplaced {{var}} tokens."""
        from lib.diagnosis.prompts import substitute

        with pytest.raises(KeyError):
            substitute("{{greeting}}, {{name}}!", {"greeting": "Hi"})
        # name is missing; must raise, not return "Hi, {{name}}!"

    def test_substitute_extra_keys_are_allowed(self) -> None:
        """substitute allows extra keys in variables that are not in the template."""
        from lib.diagnosis.prompts import substitute

        result = substitute("Hello {{name}}!", {"name": "Steph", "unused": "ignored"})
        assert result == "Hello Steph!"


# ---------------------------------------------------------------------------
# agent.py — AgentResponse and DiagnosisAgent Protocol
# ---------------------------------------------------------------------------


class TestAgentResponse:
    def test_agent_response_is_frozen_dataclass(self) -> None:
        """AgentResponse is a frozen dataclass."""
        from lib.diagnosis.agent import AgentResponse

        r = AgentResponse(text="hi", model="claude-test", input_tokens=5, output_tokens=3)
        assert r.text == "hi"
        assert r.model == "claude-test"
        assert r.input_tokens == 5
        assert r.output_tokens == 3

    def test_agent_response_is_immutable(self) -> None:
        """AgentResponse raises FrozenInstanceError on mutation attempt."""
        from lib.diagnosis.agent import AgentResponse

        r = AgentResponse(text="hi", model="m", input_tokens=1, output_tokens=1)
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            r.text = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# anthropic_agent.py — AnthropicAgent
# ---------------------------------------------------------------------------


class TestAnthropicAgent:
    def _make_mock_response(
        self, text: str, input_tokens: int, output_tokens: int, model: str
    ) -> MagicMock:
        """Build a mock that resembles the anthropic SDK Message response."""
        content_block = MagicMock()
        content_block.text = text

        usage = MagicMock()
        usage.input_tokens = input_tokens
        usage.output_tokens = output_tokens

        msg = MagicMock()
        msg.content = [content_block]
        msg.usage = usage
        msg.model = model
        return msg

    def test_run_returns_agent_response_with_correct_fields(
        self, tmp_path: Path
    ) -> None:
        """AnthropicAgent.run returns AgentResponse with correct text and token counts."""
        # Set up prompt file
        prompt_dir = tmp_path / "hello_world"
        prompt_dir.mkdir()
        (prompt_dir / "v1_baseline.md").write_text("Greet {{name}}.")

        mock_response = self._make_mock_response(
            text="Hi Steph!", input_tokens=10, output_tokens=5, model="claude-opus-4-7"
        )

        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch("lib.diagnosis.anthropic_agent.anthropic.Anthropic") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            from lib.diagnosis.anthropic_agent import AnthropicAgent

            agent = AnthropicAgent(prompts_root=tmp_path)
            result = agent.run("hello_world", {"name": "Steph"})

        assert result.text == "Hi Steph!"
        assert result.input_tokens == 10
        assert result.output_tokens == 5

    def test_run_model_matches_configured_model(self, tmp_path: Path) -> None:
        """AgentResponse.model reflects the configured model ID."""
        prompt_dir = tmp_path / "hello_world"
        prompt_dir.mkdir()
        (prompt_dir / "v1_baseline.md").write_text("Greet {{name}}.")

        mock_response = self._make_mock_response(
            text="Hello!", input_tokens=5, output_tokens=2, model="claude-opus-4-7-20251101"
        )

        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key", "ANTHROPIC_MODEL": "claude-opus-4-7"}),
            patch("lib.diagnosis.anthropic_agent.anthropic.Anthropic") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            from lib.diagnosis.anthropic_agent import AnthropicAgent

            agent = AnthropicAgent(prompts_root=tmp_path)
            result = agent.run("hello_world", {"name": "Steph"})

        assert result.model == "claude-opus-4-7"

    def test_run_missing_api_key_raises_config_error(self, tmp_path: Path) -> None:
        """AnthropicAgent.run raises ConfigError when ANTHROPIC_API_KEY is not set."""
        prompt_dir = tmp_path / "hello_world"
        prompt_dir.mkdir()
        (prompt_dir / "v1_baseline.md").write_text("Greet {{name}}.")

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        with patch.dict(os.environ, env, clear=True):
            from lib.diagnosis.anthropic_agent import AnthropicAgent
            from lib.diagnosis.agent import ConfigError

            agent = AnthropicAgent(prompts_root=tmp_path)
            with pytest.raises(ConfigError) as exc_info:
                agent.run("hello_world", {"name": "Steph"})

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_run_sdk_error_propagates_as_api_error(self, tmp_path: Path) -> None:
        """AnthropicAgent.run propagates SDK APIError when the client raises it."""
        import anthropic

        prompt_dir = tmp_path / "hello_world"
        prompt_dir.mkdir()
        (prompt_dir / "v1_baseline.md").write_text("Greet {{name}}.")

        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
            patch("lib.diagnosis.anthropic_agent.anthropic.Anthropic") as mock_client_cls,
        ):
            mock_client = MagicMock()
            mock_client_cls.return_value = mock_client
            # Simulate an SDK-level API error
            mock_client.messages.create.side_effect = anthropic.APIStatusError(
                "rate limit",
                response=MagicMock(status_code=429),
                body={"error": {"type": "rate_limit_error", "message": "rate limit"}},
            )

            from lib.diagnosis.anthropic_agent import AnthropicAgent

            agent = AnthropicAgent(prompts_root=tmp_path)
            with pytest.raises(anthropic.APIError):
                agent.run("hello_world", {"name": "Steph"})


# ---------------------------------------------------------------------------
# Import hygiene — lib/diagnosis must not import FastAPI
# ---------------------------------------------------------------------------


class TestImportHygiene:
    def test_diagnosis_modules_do_not_import_fastapi_by_source(self) -> None:
        """All source files in lib/diagnosis/ must not contain FastAPI imports."""
        diagnosis_dir = DIAGNOSIS_PKG
        assert diagnosis_dir.exists(), f"Expected {diagnosis_dir} to exist"

        forbidden = {"fastapi", "starlette"}
        for py_file in diagnosis_dir.rglob("*.py"):
            source = py_file.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for bad in forbidden:
                            assert bad not in alias.name, (
                                f"{py_file.name} imports forbidden module '{alias.name}'"
                            )
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for bad in forbidden:
                        assert bad not in module, (
                            f"{py_file.name} imports from forbidden module '{module}'"
                        )


# ---------------------------------------------------------------------------
# Integration test (live API call — skipped without API key)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping live integration test",
)
def test_anthropic_agent_live_smoke() -> None:
    """Live smoke test: actually calls the Anthropic API and expects a non-empty response.

    This test is skipped automatically when ANTHROPIC_API_KEY is not set.
    Run manually to verify real API wiring before merging.
    """
    from lib.diagnosis.anthropic_agent import AnthropicAgent

    agent = AnthropicAgent()
    result = agent.run("hello_world", {"name": "Steph"})

    assert isinstance(result.text, str)
    assert len(result.text) > 0
    assert result.input_tokens > 0
    assert result.output_tokens > 0
    assert result.model
