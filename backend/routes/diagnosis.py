"""Diagnosis route — POST /diagnosis/run.

Thin handler: load photo bytes, construct agent factory, run multi-agent
diagnosis, return DiagnosisResult. All business logic in lib/diagnosis/.
"""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from lib.diagnosis.agent import ConfigError
from lib.diagnosis.anthropic_agent import AnthropicAgent
from lib.diagnosis.multi_agent import (
    AllSpecialistsFailedError,
    CoordinatorParseError,
    DiagnosisResult,
    Issue,
    run_diagnosis,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["diagnosis"])

# Base directory for photo storage — can be overridden in tests via patch
_BASE_DIR = Path(__file__).parent.parent / ".tmp"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class DiagnosisRunRequest(BaseModel):
    """Request body for POST /diagnosis/run."""

    measurement_id: str = Field(..., min_length=1)
    photo_ids: Annotated[list[str], Field(min_length=1, max_length=3)]


class IssueOut(BaseModel):
    """A single fit issue in the response."""

    issue_type: str
    confidence: float
    description: str
    recommended_adjustment: str


class DiagnosisRunResponse(BaseModel):
    """Response body for POST /diagnosis/run."""

    issues: list[IssueOut]
    primary_recommendation: str
    cascade_type: str


# ---------------------------------------------------------------------------
# Dependency / factory
# ---------------------------------------------------------------------------


def get_agent() -> AnthropicAgent:
    """Return the AnthropicAgent instance used by the diagnosis endpoint.

    Extracted so tests can patch it cleanly.
    """
    return AnthropicAgent()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


def _resolve_crop_path(measurement_id: str, photo_id: str) -> Path:
    """Resolve the segmented crop path for a photo.

    Raises FileNotFoundError if the original photo or its crop does not exist.

    Args:
        measurement_id: Session ID owning this photo.
        photo_id: UUID4 of the photo.

    Returns:
        Path to the segmented crop PNG.

    Raises:
        FileNotFoundError: If original photo or crop not found.
    """
    base_dir = _BASE_DIR
    photo_dir = base_dir / "photos" / measurement_id

    # Find original photo (any extension)
    matches = list(photo_dir.glob(f"{photo_id}.*")) if photo_dir.exists() else []
    # Filter out segmented directory entries
    matches = [m for m in matches if m.is_file()]
    if not matches:
        raise FileNotFoundError(
            f"No photo found for measurement_id={measurement_id!r}, photo_id={photo_id!r}"
        )

    # Derive crop path
    original_path = matches[0]
    crop_path = original_path.parent / "segmented" / f"{photo_id}_cropped.png"
    if not crop_path.exists():
        raise FileNotFoundError(f"No segmented crop found for photo_id={photo_id!r}")

    return crop_path


def _issue_to_out(issue: Issue) -> IssueOut:
    """Convert an Issue dataclass to an IssueOut Pydantic model."""
    return IssueOut(
        issue_type=issue.issue_type,
        confidence=issue.confidence,
        description=issue.description,
        recommended_adjustment=issue.recommended_adjustment,
    )


@router.post("/diagnosis/run", response_model=DiagnosisRunResponse)
async def diagnosis_run(req: DiagnosisRunRequest) -> DiagnosisRunResponse:
    """Run multi-agent fit diagnosis on segmented muslin photos.

    Loads segmented crop bytes for each photo_id, fans out to three specialist
    agents, synthesises via coordinator, and returns DiagnosisResult.

    Errors:
        404 — unknown measurement_id or photo_id with no segmented crop.
        422 — validation error (empty photo_ids, >3 photo_ids, empty measurement_id).
        500 — ANTHROPIC_API_KEY missing.
        502 — all specialists failed or coordinator parse error.
    """
    # Resolve all photo crops (fail fast if any missing)
    image_bytes: list[bytes] = []
    for photo_id in req.photo_ids:
        try:
            crop_path = _resolve_crop_path(req.measurement_id, photo_id)
        except FileNotFoundError as exc:
            logger.warning("Photo not found: %s", exc)
            raise HTTPException(status_code=404, detail="Photo not found") from exc
        image_bytes.append(crop_path.read_bytes())

    # Build agent factory
    def agent_factory() -> AnthropicAgent:
        return get_agent()

    # Run diagnosis
    try:
        result: DiagnosisResult = await run_diagnosis(image_bytes, agent_factory)
    except ConfigError as exc:
        logger.warning("Config error during diagnosis: %s", exc)
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured") from exc
    except (AllSpecialistsFailedError, CoordinatorParseError) as exc:
        logger.error("Diagnosis service error: %s", exc)
        raise HTTPException(status_code=502, detail="Diagnosis service error") from exc

    return DiagnosisRunResponse(
        issues=[_issue_to_out(i) for i in result.issues],
        primary_recommendation=result.primary_recommendation,
        cascade_type=result.cascade_type,
    )
