"""Unit tests for multi_agent.py — run_diagnosis orchestration.

Tests use mocked agents. All non-integration tests pass without an API key.
"""

import asyncio
import logging
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_response(text: str) -> MagicMock:
    """Build a mock AgentResponse."""
    from lib.diagnosis.agent import AgentResponse

    return AgentResponse(text=text, model="claude-opus-4-7", input_tokens=10, output_tokens=20)


def _make_specialist_json(region: str, issue_type: str = "test_issue") -> str:
    """Build a valid specialist JSON response string."""
    import json

    return json.dumps(
        {
            "region": region,
            "issues": [
                {
                    "issue_type": issue_type,
                    "confidence": 0.8,
                    "description": f"Test issue for {region}",
                    "recommended_adjustment": "Test adjustment",
                }
            ],
        }
    )


def _make_coordinator_json(cascade_type: str = "fba") -> str:
    """Build a valid coordinator JSON response string."""
    import json

    return json.dumps(
        {
            "issues": [
                {
                    "issue_type": "pulling_across_bust",
                    "confidence": 0.85,
                    "description": "Main issue found",
                    "recommended_adjustment": "Full bust adjustment",
                }
            ],
            "primary_recommendation": "Perform a full bust adjustment",
            "cascade_type": cascade_type,
        }
    )


def _make_mock_agent(responses: list[str]) -> MagicMock:
    """Build a mock DiagnosisAgent that returns responses in order."""
    agent = MagicMock()
    agent.run.side_effect = [_make_agent_response(r) for r in responses]
    return agent


def _make_agent_factory(agent: MagicMock) -> "Callable[[], MagicMock]":  # type: ignore[type-arg]
    """Return a factory that always returns the given agent."""
    from typing import Callable

    def factory() -> MagicMock:
        return agent

    return factory


# ---------------------------------------------------------------------------
# run_diagnosis — happy path
# ---------------------------------------------------------------------------


class TestRunDiagnosisHappyPath:
    async def test_three_specialists_returns_diagnosis_result(self, tmp_path: Path) -> None:
        """run_diagnosis with three successful specialists returns a DiagnosisResult."""
        from lib.diagnosis.multi_agent import DiagnosisResult, run_diagnosis

        bust_json = _make_specialist_json("bust", "pulling_across_bust")
        waist_json = _make_specialist_json("waist_hip", "excess_fabric")
        back_json = _make_specialist_json("back", "swayback")
        coordinator_json = _make_coordinator_json("fba")

        mock_agent = _make_mock_agent(
            [bust_json, waist_json, back_json, coordinator_json]
        )

        # Set up prompt files in tmp_path
        for subdir in ["diagnosis/bust", "diagnosis/waist_hip", "diagnosis/back", "diagnosis/coordinator"]:
            (tmp_path / subdir).mkdir(parents=True, exist_ok=True)
        (tmp_path / "diagnosis/bust/v1_baseline.md").write_text("Analyze bust fit.")
        (tmp_path / "diagnosis/waist_hip/v1_baseline.md").write_text("Analyze waist/hip fit.")
        (tmp_path / "diagnosis/back/v1_baseline.md").write_text("Analyze back fit.")
        (tmp_path / "diagnosis/coordinator/v1_baseline.md").write_text(
            "Synthesise: {{specialist_outputs}}"
        )

        images = [b"fake_image_bytes_1", b"fake_image_bytes_2"]

        with patch("lib.diagnosis.multi_agent._PROMPTS_ROOT", tmp_path):
            result = await run_diagnosis(images, _make_agent_factory(mock_agent))

        assert isinstance(result, DiagnosisResult)
        assert result.cascade_type in {"fba", "swayback", "none"}

    async def test_three_specialists_coordinator_called_with_all_outputs(
        self, tmp_path: Path
    ) -> None:
        """Coordinator prompt is rendered with all three specialist outputs."""
        from lib.diagnosis.multi_agent import run_diagnosis

        bust_json = _make_specialist_json("bust", "pulling")
        waist_json = _make_specialist_json("waist_hip", "excess")
        back_json = _make_specialist_json("back", "pooling")
        coordinator_json = _make_coordinator_json("fba")

        mock_agent = _make_mock_agent(
            [bust_json, waist_json, back_json, coordinator_json]
        )

        for subdir in ["diagnosis/bust", "diagnosis/waist_hip", "diagnosis/back", "diagnosis/coordinator"]:
            (tmp_path / subdir).mkdir(parents=True, exist_ok=True)
        (tmp_path / "diagnosis/bust/v1_baseline.md").write_text("Bust prompt.")
        (tmp_path / "diagnosis/waist_hip/v1_baseline.md").write_text("Waist/hip prompt.")
        (tmp_path / "diagnosis/back/v1_baseline.md").write_text("Back prompt.")
        (tmp_path / "diagnosis/coordinator/v1_baseline.md").write_text(
            "Synthesise: {{specialist_outputs}}"
        )

        images = [b"img"]

        with patch("lib.diagnosis.multi_agent._PROMPTS_ROOT", tmp_path):
            await run_diagnosis(images, _make_agent_factory(mock_agent))

        # The 4th call (index 3) is the coordinator
        coordinator_call = mock_agent.run.call_args_list[3]
        variables = coordinator_call[0][1] if coordinator_call[0] else coordinator_call[1].get("variables", {})
        specialist_outputs = variables.get("specialist_outputs", "")
        # All three regions should appear in the serialised JSON
        assert "bust" in specialist_outputs
        assert "waist_hip" in specialist_outputs
        assert "back" in specialist_outputs


# ---------------------------------------------------------------------------
# run_diagnosis — timing (concurrency)
# ---------------------------------------------------------------------------


class TestRunDiagnosisConcurrency:
    async def test_three_100ms_specialists_complete_under_200ms(
        self, tmp_path: Path
    ) -> None:
        """Three specialists each delayed 100 ms must complete in < 200 ms (proves gather concurrency)."""
        import json

        from lib.diagnosis.multi_agent import run_diagnosis

        def slow_run(prompt_name: str, variables: dict, images=None, max_tokens: int = 256):
            time.sleep(0.1)  # sync sleep — runs in thread via asyncio.to_thread
            region_map = {
                "diagnosis/bust": "bust",
                "diagnosis/waist_hip": "waist_hip",
                "diagnosis/back": "back",
                "diagnosis/coordinator": "coordinator",
            }
            region = region_map.get(prompt_name, "bust")

            if region == "coordinator":
                return _make_agent_response(_make_coordinator_json("fba"))
            return _make_agent_response(_make_specialist_json(region))

        slow_agent = MagicMock()
        slow_agent.run.side_effect = slow_run

        for subdir in ["diagnosis/bust", "diagnosis/waist_hip", "diagnosis/back", "diagnosis/coordinator"]:
            (tmp_path / subdir).mkdir(parents=True, exist_ok=True)
        (tmp_path / "diagnosis/bust/v1_baseline.md").write_text("Bust.")
        (tmp_path / "diagnosis/waist_hip/v1_baseline.md").write_text("Waist/hip.")
        (tmp_path / "diagnosis/back/v1_baseline.md").write_text("Back.")
        (tmp_path / "diagnosis/coordinator/v1_baseline.md").write_text(
            "Synthesise: {{specialist_outputs}}"
        )

        images = [b"img"]

        start = time.monotonic()
        with patch("lib.diagnosis.multi_agent._PROMPTS_ROOT", tmp_path):
            await run_diagnosis(images, lambda: slow_agent)
        elapsed = time.monotonic() - start

        assert elapsed < 0.2, f"Expected < 200ms for concurrent specialists, got {elapsed:.3f}s"


# ---------------------------------------------------------------------------
# run_diagnosis — partial failure
# ---------------------------------------------------------------------------


class TestRunDiagnosisPartialFailure:
    async def test_one_specialist_fails_coordinator_runs_with_survivors(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When one specialist fails, coordinator runs with the remaining two survivors."""
        from lib.diagnosis.multi_agent import DiagnosisResult, run_diagnosis

        call_count = [0]

        def failing_run(prompt_name: str, variables: dict, images=None, max_tokens: int = 256):
            call_count[0] += 1
            if "bust" in prompt_name:
                raise RuntimeError("bust specialist failed")
            if "waist_hip" in prompt_name:
                return _make_agent_response(_make_specialist_json("waist_hip"))
            if "back" in prompt_name:
                return _make_agent_response(_make_specialist_json("back"))
            # coordinator
            return _make_agent_response(_make_coordinator_json("swayback"))

        mock_agent = MagicMock()
        mock_agent.run.side_effect = failing_run

        for subdir in ["diagnosis/bust", "diagnosis/waist_hip", "diagnosis/back", "diagnosis/coordinator"]:
            (tmp_path / subdir).mkdir(parents=True, exist_ok=True)
        (tmp_path / "diagnosis/bust/v1_baseline.md").write_text("Bust.")
        (tmp_path / "diagnosis/waist_hip/v1_baseline.md").write_text("Waist/hip.")
        (tmp_path / "diagnosis/back/v1_baseline.md").write_text("Back.")
        (tmp_path / "diagnosis/coordinator/v1_baseline.md").write_text(
            "Synthesise: {{specialist_outputs}}"
        )

        images = [b"img"]

        with caplog.at_level(logging.WARNING, logger="lib.diagnosis.multi_agent"):
            with patch("lib.diagnosis.multi_agent._PROMPTS_ROOT", tmp_path):
                result = await run_diagnosis(images, lambda: mock_agent)

        # Result should still come through
        assert isinstance(result, DiagnosisResult)
        # Warning logged naming the failed region
        assert any("bust" in record.message for record in caplog.records)

    async def test_one_specialist_fails_warning_names_region(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A warning log message names the failed specialist region."""
        from lib.diagnosis.multi_agent import run_diagnosis

        def failing_run(prompt_name: str, variables: dict, images=None, max_tokens: int = 256):
            if "waist_hip" in prompt_name:
                raise ValueError("waist_hip error")
            if "bust" in prompt_name:
                return _make_agent_response(_make_specialist_json("bust"))
            if "back" in prompt_name:
                return _make_agent_response(_make_specialist_json("back"))
            return _make_agent_response(_make_coordinator_json("fba"))

        mock_agent = MagicMock()
        mock_agent.run.side_effect = failing_run

        for subdir in ["diagnosis/bust", "diagnosis/waist_hip", "diagnosis/back", "diagnosis/coordinator"]:
            (tmp_path / subdir).mkdir(parents=True, exist_ok=True)
        (tmp_path / "diagnosis/bust/v1_baseline.md").write_text("Bust.")
        (tmp_path / "diagnosis/waist_hip/v1_baseline.md").write_text("Waist/hip.")
        (tmp_path / "diagnosis/back/v1_baseline.md").write_text("Back.")
        (tmp_path / "diagnosis/coordinator/v1_baseline.md").write_text(
            "Synthesise: {{specialist_outputs}}"
        )

        images = [b"img"]

        with caplog.at_level(logging.WARNING, logger="lib.diagnosis.multi_agent"):
            with patch("lib.diagnosis.multi_agent._PROMPTS_ROOT", tmp_path):
                await run_diagnosis(images, lambda: mock_agent)

        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("waist_hip" in msg for msg in warning_messages)


# ---------------------------------------------------------------------------
# run_diagnosis — total failure
# ---------------------------------------------------------------------------


class TestRunDiagnosisTotalFailure:
    async def test_all_three_specialists_fail_raises_all_specialists_failed(
        self, tmp_path: Path
    ) -> None:
        """AllSpecialistsFailedError raised when all three specialists fail."""
        from lib.diagnosis.multi_agent import AllSpecialistsFailedError, run_diagnosis

        mock_agent = MagicMock()
        mock_agent.run.side_effect = RuntimeError("all fail")

        for subdir in ["diagnosis/bust", "diagnosis/waist_hip", "diagnosis/back", "diagnosis/coordinator"]:
            (tmp_path / subdir).mkdir(parents=True, exist_ok=True)
        (tmp_path / "diagnosis/bust/v1_baseline.md").write_text("Bust.")
        (tmp_path / "diagnosis/waist_hip/v1_baseline.md").write_text("Waist/hip.")
        (tmp_path / "diagnosis/back/v1_baseline.md").write_text("Back.")
        (tmp_path / "diagnosis/coordinator/v1_baseline.md").write_text(
            "Synthesise: {{specialist_outputs}}"
        )

        images = [b"img"]

        with pytest.raises(AllSpecialistsFailedError):
            with patch("lib.diagnosis.multi_agent._PROMPTS_ROOT", tmp_path):
                await run_diagnosis(images, lambda: mock_agent)


# ---------------------------------------------------------------------------
# run_diagnosis — coordinator parse error
# ---------------------------------------------------------------------------


class TestRunDiagnosisCoordinatorError:
    async def test_coordinator_parse_error_propagates(self, tmp_path: Path) -> None:
        """CoordinatorParseError from coordinator propagates out of run_diagnosis."""
        from lib.diagnosis.multi_agent import CoordinatorParseError, run_diagnosis

        bust_json = _make_specialist_json("bust")
        waist_json = _make_specialist_json("waist_hip")
        back_json = _make_specialist_json("back")
        bad_coordinator = '{"issues": [], "primary_recommendation": "ok", "cascade_type": "banana"}'

        mock_agent = _make_mock_agent([bust_json, waist_json, back_json, bad_coordinator])

        for subdir in ["diagnosis/bust", "diagnosis/waist_hip", "diagnosis/back", "diagnosis/coordinator"]:
            (tmp_path / subdir).mkdir(parents=True, exist_ok=True)
        (tmp_path / "diagnosis/bust/v1_baseline.md").write_text("Bust.")
        (tmp_path / "diagnosis/waist_hip/v1_baseline.md").write_text("Waist/hip.")
        (tmp_path / "diagnosis/back/v1_baseline.md").write_text("Back.")
        (tmp_path / "diagnosis/coordinator/v1_baseline.md").write_text(
            "Synthesise: {{specialist_outputs}}"
        )

        images = [b"img"]

        with pytest.raises(CoordinatorParseError):
            with patch("lib.diagnosis.multi_agent._PROMPTS_ROOT", tmp_path):
                await run_diagnosis(images, lambda: mock_agent)
