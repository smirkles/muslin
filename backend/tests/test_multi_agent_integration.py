"""Integration test for multi-agent diagnosis — requires ANTHROPIC_API_KEY.

Skipped automatically when the key is not set. Run manually to verify real
API wiring before merging. The fixture photo is a small synthetic PNG that
exercises the full pipeline without needing a real muslin photo.
"""

import os
from pathlib import Path

import pytest

FIXTURE_CROP = Path(__file__).parent / "fixtures" / "diagnosis" / "sample_front.png"


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set — skipping live integration test",
)
def test_multi_agent_diagnosis_live_pipeline() -> None:
    """Live smoke test: runs full multi-agent diagnosis against a fixture PNG.

    Asserts that the returned cascade_type is in the valid closed set.
    """
    import asyncio

    from lib.diagnosis.anthropic_agent import AnthropicAgent
    from lib.diagnosis.multi_agent import run_diagnosis

    assert FIXTURE_CROP.exists(), f"Fixture PNG not found at {FIXTURE_CROP}"

    image_bytes = FIXTURE_CROP.read_bytes()

    def agent_factory() -> AnthropicAgent:
        return AnthropicAgent()

    result = asyncio.run(run_diagnosis([image_bytes], agent_factory))

    assert result.cascade_type in {
        "fba",
        "swayback",
        "none",
    }, f"Unexpected cascade_type={result.cascade_type!r}"
    assert isinstance(result.primary_recommendation, str)
    assert len(result.primary_recommendation) > 0
    assert isinstance(result.issues, list)
