"""Patterns route — GET /patterns and GET /patterns/{pattern_id}.

Thin handlers: delegate all logic to lib.pattern_registry.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
