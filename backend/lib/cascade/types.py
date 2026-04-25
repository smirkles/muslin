"""Shared cascade data types.

These types are the contract between backend cascade engines and the
frontend CascadePlayer. Do not change field names without updating both sides.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lib.pattern_ops import Pattern


@dataclass(frozen=True)
class CascadeStep:
    """One animated step in a cascade sequence."""

    step_number: int
    narration: str
    svg: str  # full SVG string for this step's visual state


@dataclass
class CascadeScript:
    """Ordered sequence of steps produced by a cascade function."""

    adjustment_type: str
    pattern_id: str
    amount_cm: float
    steps: list[CascadeStep]
    seam_adjustments: dict[str, float] = field(default_factory=dict)


@dataclass
class CascadeResult:
    """Output of a cascade function: adjusted pattern + animation script."""

    adjusted_pattern: Pattern
    cascade_script: CascadeScript
