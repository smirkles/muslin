"""Patterns route — GET /patterns, GET /patterns/{pattern_id}, POST /patterns/{pattern_id}/grade.

Thin handlers: delegate all logic to lib.pattern_registry and lib.grading.
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lib.grading import (
    BaseMeasurements,
    grade_pattern,
    store_graded_pattern,
)
from lib.measurements import get_measurements
from lib.pattern_ops import PatternError, load_pattern
from lib.pattern_registry import REGISTRY, PatternNotFound, get_pattern

router = APIRouter(tags=["patterns"])


# ---------------------------------------------------------------------------
# Response schemas (Pydantic models for serialisation)
# ---------------------------------------------------------------------------


class PatternMetaResponse(BaseModel):
    """Serialisable metadata for a single pattern (list response)."""

    id: str
    name: str
    description: str
    piece_count: int

    model_config = {"from_attributes": True}


class PatternDetailResponse(PatternMetaResponse):
    """Full pattern detail including SVG content (single-pattern response)."""

    svg: str


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


@router.get("/patterns", response_model=list[PatternMetaResponse])
def list_patterns() -> list[PatternMetaResponse]:
    """Return metadata for all registered patterns."""
    return [PatternMetaResponse.model_validate(meta) for meta in REGISTRY.values()]


@router.get("/patterns/{pattern_id}", response_model=PatternDetailResponse)
def get_pattern_route(pattern_id: str) -> PatternDetailResponse:
    """Return full detail (metadata + SVG) for a single pattern by id."""
    try:
        detail = get_pattern(REGISTRY, pattern_id)
    except PatternNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PatternDetailResponse.model_validate(detail)


# ---------------------------------------------------------------------------
# Grade route
# ---------------------------------------------------------------------------


class GradeRequest(BaseModel):
    """Request body for POST /patterns/{pattern_id}/grade."""

    measurement_id: str


class GradedPatternResponse(BaseModel):
    """Response body for a successful grading operation."""

    graded_pattern_id: str
    pattern_id: str
    measurement_id: str
    svg: str
    adjustments_cm: dict[str, float]


@router.post("/patterns/{pattern_id}/grade", response_model=GradedPatternResponse)
def grade_pattern_route(pattern_id: str, body: GradeRequest) -> GradedPatternResponse:
    """Grade a registered pattern to user measurements; return the graded SVG.

    Errors:
    - 404 if pattern_id not in registry.
    - 404 if measurement_id not in session store.
    - 422 if body is missing or malformed (FastAPI validation).
    - 500 if pattern SVG cannot be parsed or required element missing.
    """
    # Look up the pattern in the registry
    meta = REGISTRY.get(pattern_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Pattern '{pattern_id}' not found")

    # Look up the measurements in the session store
    try:
        user_meas = get_measurements(body.measurement_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Measurements '{body.measurement_id}' not found",
        ) from exc

    # Build base measurements from pattern metadata
    if any(
        v is None
        for v in (
            meta.base_bust_cm,
            meta.base_waist_cm,
            meta.base_hip_cm,
            meta.base_back_length_cm,
        )
    ):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to grade pattern: pattern '{pattern_id}' has no base measurements",
        )

    base_meas = BaseMeasurements(
        bust_cm=cast(float, meta.base_bust_cm),
        waist_cm=cast(float, meta.base_waist_cm),
        hip_cm=cast(float, meta.base_hip_cm),
        back_length_cm=cast(float, meta.base_back_length_cm),
    )

    # Load and grade the pattern
    try:
        pattern = load_pattern(meta.svg_path)
        graded = grade_pattern(
            pattern,
            base_meas,
            user_meas,
            pattern_id=pattern_id,
            measurement_id=body.measurement_id,
        )
    except PatternError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to grade pattern: {exc}",
        ) from exc

    store_graded_pattern(graded)

    return GradedPatternResponse(
        graded_pattern_id=graded.graded_pattern_id,
        pattern_id=graded.pattern_id,
        measurement_id=graded.measurement_id,
        svg=graded.svg,
        adjustments_cm=graded.adjustments_cm,
    )
