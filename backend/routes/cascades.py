"""Cascade routes — POST /cascades/apply-adjustment."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from lib.cascade.swayback import apply_swayback
from lib.pattern_ops import ElementNotFound
from lib.pattern_registry import REGISTRY, PatternNotFound, get_pattern

router = APIRouter(prefix="/cascades", tags=["cascades"])

# Dispatch table — spec 15 adds "fba": apply_fba
ADJUSTMENTS = {
    "swayback": apply_swayback,
}


class ApplyAdjustmentRequest(BaseModel):
    pattern_id: str
    adjustment_type: str
    amount_cm: float


class CascadeStepResponse(BaseModel):
    step_number: int
    narration: str
    svg: str


class CascadeScriptResponse(BaseModel):
    adjustment_type: str
    pattern_id: str
    amount_cm: float
    steps: list[CascadeStepResponse]
    seam_adjustments: dict[str, float]


@router.post("/apply-adjustment", response_model=CascadeScriptResponse)
def apply_adjustment(req: ApplyAdjustmentRequest) -> CascadeScriptResponse:
    """Apply a named adjustment cascade to a pattern and return the cascade script."""
    # Validate adjustment type
    if req.adjustment_type not in ADJUSTMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown adjustment type: '{req.adjustment_type}'",
        )

    # Load pattern
    try:
        detail = get_pattern(REGISTRY, req.pattern_id)
    except PatternNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    from lib.pattern_ops import load_pattern

    pattern = load_pattern(detail.svg_path)

    # Apply cascade
    fn = ADJUSTMENTS[req.adjustment_type]
    try:
        result = fn(pattern, req.amount_cm, pattern_id=req.pattern_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ElementNotFound as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Pattern element '{exc}' not found",
        ) from exc

    script = result.cascade_script
    return CascadeScriptResponse(
        adjustment_type=script.adjustment_type,
        pattern_id=script.pattern_id,
        amount_cm=script.amount_cm,
        steps=[
            CascadeStepResponse(
                step_number=s.step_number,
                narration=s.narration,
                svg=s.svg,
            )
            for s in script.steps
        ],
        seam_adjustments=script.seam_adjustments,
    )
