"""Swayback cascade — removes excess fabric at centre back waist.

Algorithm:
1. Render base pattern.
2. Draw a horizontal fold line at WAIST_Y across the full back width.
3. Rotate back-piece-lower around the side-seam pivot by a small negative angle,
   closing a wedge at CB and leaving the side seam invariant.
4. True the back side seam.
5. True the centre back seam.
"""

from __future__ import annotations

import math

from lib.cascade.constants import CB_X, SCALE, SIDE_SEAM_X, WAIST_Y
from lib.cascade.prompts import load_narration
from lib.cascade.types import CascadeResult, CascadeScript, CascadeStep
from lib.pattern_ops import Pattern, render_pattern, rotate_element, slash_line, true_seam_length

_MIN_AMOUNT_CM = 0.5
_MAX_AMOUNT_CM = 2.5


def apply_swayback(
    pattern: Pattern,
    swayback_amount_cm: float,
    pattern_id: str = "bodice-v1",
) -> CascadeResult:
    """Apply a swayback adjustment and return a CascadeResult with 5 steps.

    Args:
        pattern: Loaded bodice-v1 pattern. Must contain back-piece-lower,
            back-cb-seam, back-side-seam and their reference counterparts.
        swayback_amount_cm: Amount to remove at centre back, in cm.
            Valid range: [0.5, 2.5].
        pattern_id: Pattern identifier recorded in the cascade script.

    Returns:
        CascadeResult with adjusted_pattern and cascade_script (5 steps).

    Raises:
        ValueError: If swayback_amount_cm is outside the valid range.
    """
    if swayback_amount_cm < _MIN_AMOUNT_CM:
        raise ValueError(
            f"swayback_amount_cm must be between {_MIN_AMOUNT_CM} and {_MAX_AMOUNT_CM}, "
            f"got {swayback_amount_cm}"
        )
    if swayback_amount_cm > _MAX_AMOUNT_CM:
        raise ValueError(
            f"swayback_amount_cm must be between {_MIN_AMOUNT_CM} and {_MAX_AMOUNT_CM}, "
            f"got {swayback_amount_cm}"
        )

    narration = load_narration("swayback")

    swayback_px = swayback_amount_cm * SCALE
    # Negative angle = counter-clockwise in SVG y-down = fold up at CB
    angle_deg = -math.degrees(math.atan2(swayback_px, SIDE_SEAM_X - CB_X))
    pivot = (SIDE_SEAM_X, WAIST_Y)

    steps: list[CascadeStep] = []

    # Step 1 — base pattern
    p = pattern
    steps.append(
        CascadeStep(
            step_number=1,
            narration=narration["step_1_intro"],
            svg=render_pattern(p),
        )
    )

    # Step 2 — draw fold line at waist
    p = slash_line(p, (CB_X, WAIST_Y), (SIDE_SEAM_X, WAIST_Y), "swayback-fold-line")
    steps.append(
        CascadeStep(
            step_number=2,
            narration=narration["step_2_fold_line"],
            svg=render_pattern(p),
        )
    )

    # Step 3 — rotate lower back piece around side-seam pivot
    p = rotate_element(p, "back-piece-lower", angle_deg, pivot)
    steps.append(
        CascadeStep(
            step_number=3,
            narration=narration["step_3_fold_wedge"].format(amount_cm=swayback_amount_cm),
            svg=render_pattern(p),
        )
    )

    # Step 4 — true the side seam
    p = true_seam_length(p, "back-side-seam", "back-side-seam-reference")
    steps.append(
        CascadeStep(
            step_number=4,
            narration=narration["step_4_true_side_seam"],
            svg=render_pattern(p),
        )
    )

    # Step 5 — true the CB seam
    p = true_seam_length(p, "back-cb-seam", "back-cb-seam-reference")
    steps.append(
        CascadeStep(
            step_number=5,
            narration=narration["step_5_true_cb_seam"],
            svg=render_pattern(p),
        )
    )

    # Seam adjustments summary
    # CB removes swayback_amount_cm; side seam is invariant (pivot at side seam)
    waist_seam_delta = round(-swayback_amount_cm * 0.3, 2)  # approximate taper
    seam_adjustments = {
        "cb_seam_delta_cm": round(-swayback_amount_cm, 2),
        "side_seam_delta_cm": 0.0,
        "waist_seam_delta_cm": waist_seam_delta,
    }

    cascade_script = CascadeScript(
        adjustment_type="swayback",
        pattern_id=pattern_id,
        amount_cm=swayback_amount_cm,
        steps=steps,
        seam_adjustments=seam_adjustments,
    )

    return CascadeResult(
        adjusted_pattern=p,
        cascade_script=cascade_script,
    )
