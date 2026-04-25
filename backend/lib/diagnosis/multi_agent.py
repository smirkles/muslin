"""Multi-agent fit diagnosis orchestrator.

Fans out to three specialist agents (bust, waist/hip, back) concurrently,
then synthesises their outputs via a coordinator agent into a DiagnosisResult.

No FastAPI imports — this is pure lib/ code.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from lib.diagnosis.agent import DiagnosisAgent

logger = logging.getLogger(__name__)

# Default root for prompt files (two levels above backend/, then prompts/)
_PROMPTS_ROOT = Path(__file__).parent.parent.parent.parent / "prompts"

# The three specialist regions run in this order
_SPECIALIST_REGIONS: list[str] = ["bust", "waist_hip", "back"]

# Valid cascade types (closed set — coordinator must return one of these)
_VALID_CASCADE_TYPES = frozenset({"fba", "swayback", "none"})


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SpecialistParseError(Exception):
    """Raised when a specialist agent response cannot be parsed into SpecialistDiagnosis."""


class CoordinatorParseError(Exception):
    """Raised when the coordinator agent response cannot be parsed into DiagnosisResult."""


class AllSpecialistsFailedError(Exception):
    """Raised when every specialist agent call fails — diagnosis cannot proceed."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Issue:
    """A single fit issue identified by a specialist agent."""

    issue_type: str
    """Open string in v1 — will be tightened to enum in V2."""

    confidence: float
    """Confidence score in the range [0.0, 1.0]."""

    description: str
    """Human-readable description of the fit issue."""

    recommended_adjustment: str
    """Recommended pattern adjustment to address the issue."""


@dataclass(frozen=True)
class SpecialistDiagnosis:
    """Output from a single specialist agent."""

    region: Literal["bust", "waist_hip", "back"]
    """The body region this specialist examined."""

    issues: list[Issue]
    """Issues identified in this region."""


@dataclass(frozen=True)
class DiagnosisResult:
    """Final synthesised diagnosis from the coordinator agent."""

    issues: list[Issue]
    """All fit issues identified across all regions."""

    primary_recommendation: str
    """Human-readable primary recommendation."""

    cascade_type: Literal["fba", "swayback", "none"]
    """Which adjustment cascade to run next."""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _strip_code_fence(text: str) -> str:
    """Strip markdown code fence wrappers from agent text output.

    Claude sometimes wraps JSON in ```json ... ``` blocks despite being asked
    not to. This function normalises that by extracting the inner content.

    Args:
        text: Raw text output, possibly containing a code fence.

    Returns:
        The text with leading/trailing code fence markers removed, stripped.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        # Remove opening fence (```json or ``` etc.)
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        # Remove closing fence
        if stripped.endswith("```"):
            stripped = stripped[: stripped.rfind("```")]
    return stripped.strip()


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _parse_specialist(region: str, text: str) -> SpecialistDiagnosis:
    """Parse a specialist agent's text output into a SpecialistDiagnosis dataclass.

    Args:
        region: The body region (e.g. 'bust', 'waist_hip', 'back').
        text: The raw text output from the specialist agent.

    Returns:
        A populated SpecialistDiagnosis dataclass.

    Raises:
        SpecialistParseError: If the text is not valid JSON, or is missing required fields.
    """
    clean_text = _strip_code_fence(text)
    try:
        data = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        raise SpecialistParseError(
            f"Specialist ({region}) returned malformed JSON: {text}"
        ) from exc

    try:
        raw_issues = data["issues"]
        _ = data["region"]  # must exist but we use the caller-supplied region
    except (KeyError, TypeError) as exc:
        raise SpecialistParseError(
            f"Specialist ({region}) response missing required fields: {text}"
        ) from exc

    try:
        issues = [
            Issue(
                issue_type=issue["issue_type"],
                confidence=max(0.0, min(1.0, float(issue["confidence"]))),
                description=issue["description"],
                recommended_adjustment=issue["recommended_adjustment"],
            )
            for issue in raw_issues
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise SpecialistParseError(
            f"Specialist ({region}) issue missing required fields: {text}"
        ) from exc

    return SpecialistDiagnosis(region=region, issues=issues)  # type: ignore[arg-type]


def _parse_coordinator(text: str) -> DiagnosisResult:
    """Parse the coordinator agent's text output into a DiagnosisResult.

    Args:
        text: The raw text output from the coordinator agent.

    Returns:
        A populated DiagnosisResult dataclass.

    Raises:
        CoordinatorParseError: If the text is not valid JSON, is missing required fields,
            or cascade_type is not in the closed set {"fba", "swayback", "none"}.
    """
    clean_text = _strip_code_fence(text)
    try:
        data = json.loads(clean_text)
    except json.JSONDecodeError as exc:
        raise CoordinatorParseError(f"Coordinator returned malformed JSON: {text}") from exc

    try:
        cascade_type = data["cascade_type"]
        primary_recommendation = data["primary_recommendation"]
        raw_issues = data["issues"]
    except (KeyError, TypeError) as exc:
        raise CoordinatorParseError(
            f"Coordinator response missing required fields: {text}"
        ) from exc

    if cascade_type not in _VALID_CASCADE_TYPES:
        raise CoordinatorParseError(
            f"Coordinator returned invalid cascade_type={cascade_type!r}. "
            f"Must be one of {sorted(_VALID_CASCADE_TYPES)}. Raw response: {text}"
        )

    try:
        issues = [
            Issue(
                issue_type=issue["issue_type"],
                confidence=max(0.0, min(1.0, float(issue["confidence"]))),
                description=issue["description"],
                recommended_adjustment=issue["recommended_adjustment"],
            )
            for issue in raw_issues
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise CoordinatorParseError(
            f"Coordinator response issue missing required fields: {text}"
        ) from exc

    return DiagnosisResult(
        issues=issues,
        primary_recommendation=primary_recommendation,
        cascade_type=cascade_type,
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def _run_specialist(
    region: str,
    agent: DiagnosisAgent,
    images: list[bytes],
    prompts_root: Path,
) -> SpecialistDiagnosis | Exception:
    """Run a single specialist agent (sync) and return result or caught exception.

    Designed to be called via asyncio.to_thread so it does not block the event loop.
    ConfigError is re-raised (not caught) — it is a fatal configuration issue.

    Args:
        region: Body region identifier (e.g. 'bust', 'waist_hip', 'back').
        agent: The DiagnosisAgent to call.
        images: List of raw image bytes to pass to the agent.
        prompts_root: Root directory of prompt files.

    Returns:
        SpecialistDiagnosis on success, or the non-fatal Exception on failure.

    Raises:
        ConfigError: Re-raised immediately — fatal, should not be swallowed.
    """
    from lib.diagnosis.agent import ConfigError

    try:
        prompt_name = f"diagnosis/{region}"
        response = agent.run(
            prompt_name,
            variables={},
            images=images,
            max_tokens=1024,
        )
        return _parse_specialist(region, response.text)
    except ConfigError:
        # Fatal — re-raise so asyncio.gather propagates it and the route maps it to 500
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Specialist agent for region=%r failed: %s: %s",
            region,
            type(exc).__name__,
            exc,
        )
        return exc


async def run_diagnosis(
    images: list[bytes],
    agent_factory: Callable[[], DiagnosisAgent],
) -> DiagnosisResult:
    """Run multi-agent fit diagnosis on the provided images.

    Fans out to three specialist agents (bust, waist/hip, back) concurrently via
    asyncio.gather + asyncio.to_thread, then runs a coordinator agent to synthesise
    the results.

    Partial failure: if one specialist fails, the coordinator runs with the survivors.
    Total failure: if all specialists fail, raises AllSpecialistsFailedError.

    Args:
        images: List of raw image bytes (base64 encoding happens inside AnthropicAgent).
        agent_factory: Callable that produces a DiagnosisAgent instance.

    Returns:
        DiagnosisResult with synthesised issues and cascade_type.

    Raises:
        AllSpecialistsFailedError: If all specialist agents fail.
        CoordinatorParseError: If the coordinator returns an unparseable response.
    """
    prompts_root = _PROMPTS_ROOT

    # Fan out three specialists concurrently
    specialist_tasks = [
        asyncio.to_thread(_run_specialist, region, agent_factory(), images, prompts_root)
        for region in _SPECIALIST_REGIONS
    ]
    outcomes = await asyncio.gather(*specialist_tasks)

    # Separate successes from failures
    survivors: list[SpecialistDiagnosis] = []
    for region, outcome in zip(_SPECIALIST_REGIONS, outcomes, strict=True):
        if isinstance(outcome, Exception):
            logger.warning("Specialist for region=%r excluded from coordinator input", region)
        else:
            survivors.append(outcome)

    if not survivors:
        raise AllSpecialistsFailedError(
            "All three specialist agents failed — cannot produce a diagnosis"
        )

    # Serialise survivors for coordinator
    specialist_outputs = json.dumps(
        [
            {
                "region": sd.region,
                "issues": [
                    {
                        "issue_type": i.issue_type,
                        "confidence": i.confidence,
                        "description": i.description,
                        "recommended_adjustment": i.recommended_adjustment,
                    }
                    for i in sd.issues
                ],
            }
            for sd in survivors
        ]
    )

    # Run coordinator agent
    coordinator_agent = agent_factory()
    coordinator_response = await asyncio.to_thread(
        coordinator_agent.run,
        "diagnosis/coordinator",
        {"specialist_outputs": specialist_outputs},
        None,  # no images for coordinator
        1024,  # max_tokens
    )

    return _parse_coordinator(coordinator_response.text)
