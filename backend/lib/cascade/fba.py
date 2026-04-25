"""FBA (Full Bust Adjustment) cascade — adds room in the front bodice for a full bust.

Algorithm:
1. Render base pattern (no changes).
2. Draw a vertical slash line at the bust column x=BUST_COLUMN_X from top to hem.
3. Translate front-side-panel rightward by fba_px — opening the slash.
4. Add a new bust dart at the side seam edge to take in the extra fabric.

Reference: docs/specs/15-fba-cascade.md
"""

from __future__ import annotations

from lib.cascade.prompts import load_narration
from lib.cascade.types import CascadeResult, CascadeScript, CascadeStep
from lib.pattern_ops import Pattern, add_dart, render_pattern, slash_line, translate_element

# ---------------------------------------------------------------------------
# FBA-specific geometry constants — tied to bodice-v1 SVG geometry.
# Do NOT move to cascade/constants.py; these values are front-piece-specific
# and do not apply to the back bodice coordinate space.
# ---------------------------------------------------------------------------

# x-coordinate of the bust column (vertical slash position) in bodice-v1 SVG
_BUST_COLUMN_X: float = 115

# y-coordinate of the bust level (underarm-to-bust midpoint) in bodice-v1
_BUST_Y: float = 152

# y-coordinates defining the slash line extent in bodice-v1 (neckline → hem)
_SLASH_TOP_Y: float = 6
_SLASH_BOTTOM_Y: float = 360

# 1 cm = 10 mm; 1 mm = 0.5 SVG user units at bodice-v1 scale
_PX_PER_CM: float = 5.0  # same as cascade/constants.py PX_PER_CM

_MIN_AMOUNT_CM: float = 0.5
_MAX_AMOUNT_CM: float = 6.0


def apply_fba(
    pattern: Pattern,
    fba_amount_cm: float,
    pattern_id: str = "bodice-v1",
) -> CascadeResult:
    """Apply a Full Bust Adjustment and return a CascadeResult with 4 steps.

    Args:
        pattern: Loaded bodice-v1 pattern. Must contain front-cf-panel,
            front-side-panel, and front-waist-dart elements.
        fba_amount_cm: FBA amount in centimetres. Valid range: [0.5, 6.0].
        pattern_id: Pattern identifier recorded in the cascade script.

    Returns:
        CascadeResult with adjusted_pattern and cascade_script (4 steps).

    Raises:
        ValueError: If fba_amount_cm is outside the valid range.
    """
    if fba_amount_cm < _MIN_AMOUNT_CM:
        raise ValueError(
            f"fba_amount_cm must be between {_MIN_AMOUNT_CM} and {_MAX_AMOUNT_CM}, "
            f"got {fba_amount_cm}"
        )
    if fba_amount_cm > _MAX_AMOUNT_CM:
        raise ValueError(
            f"fba_amount_cm must be between {_MIN_AMOUNT_CM} and {_MAX_AMOUNT_CM}, "
            f"got {fba_amount_cm}"
        )

    # Convert cm to SVG user units (1 cm = 5 px at bodice-v1 scale)
    fba_px = fba_amount_cm * _PX_PER_CM

    narration = load_narration("fba")

    steps: list[CascadeStep] = []

    # ------------------------------------------------------------------
    # Step 1 — base pattern, no changes
    # ------------------------------------------------------------------
    p = pattern
    steps.append(
        CascadeStep(
            step_number=1,
            narration=narration["step_1_intro"],
            svg=render_pattern(p),
        )
    )

    # ------------------------------------------------------------------
    # Step 2 — draw slash line at bust column
    # ------------------------------------------------------------------
    p = slash_line(
        p,
        from_pt=(_BUST_COLUMN_X, _SLASH_TOP_Y),
        to_pt=(_BUST_COLUMN_X, _SLASH_BOTTOM_Y),
        slash_id="fba-slash-1",
    )
    steps.append(
        CascadeStep(
            step_number=2,
            narration=narration["step_2_slash_line"],
            svg=render_pattern(p),
        )
    )

    # ------------------------------------------------------------------
    # Step 3 — translate front-side-panel rightward to open the slash
    # NOTE: We use translate_element directly (not spread_at_line) because
    # spread_at_line classifies ALL elements by centroid position and would
    # incorrectly translate the back bodice pieces.
    # ------------------------------------------------------------------
    p = translate_element(p, "front-side-panel", dx=fba_px, dy=0)
    steps.append(
        CascadeStep(
            step_number=3,
            narration=narration["step_3_open_slash"].format(amount_cm=fba_amount_cm),
            svg=render_pattern(p),
        )
    )

    # ------------------------------------------------------------------
    # Step 4 — add bust dart at the side seam to take in the extra fabric
    # dart_tip_x: the spread side-panel edge (bust column + fba spread)
    # angle_deg=180: tip at position, base extends LEFTWARD toward CF
    # ------------------------------------------------------------------
    dart_tip_x = _BUST_COLUMN_X + fba_px
    p = add_dart(
        p,
        position=(dart_tip_x, _BUST_Y),
        width=fba_px * 0.8,
        length=fba_px,
        angle_deg=180,
        dart_id="front-bust-dart",
    )
    steps.append(
        CascadeStep(
            step_number=4,
            narration=narration["step_4_bust_dart"],
            svg=render_pattern(p),
        )
    )

    cascade_script = CascadeScript(
        adjustment_type="fba",
        pattern_id=pattern_id,
        amount_cm=fba_amount_cm,
        steps=steps,
        seam_adjustments={},  # seam truing is out of scope for V1 (see spec 15)
    )

    return CascadeResult(
        adjusted_pattern=p,
        cascade_script=cascade_script,
    )
