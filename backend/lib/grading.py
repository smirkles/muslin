"""Pattern grading — scale a base-size pattern to user measurements.

No FastAPI imports.  This module is pure logic and must be importable
without any HTTP framework dependencies.

Public API
----------
grade_pattern(pattern, base_measurements, user_measurements, pattern_id, measurement_id)
    → GradedPattern

store_graded_pattern(g)
    Store a GradedPattern in the in-memory session store.

get_graded_pattern(graded_pattern_id)
    Retrieve a GradedPattern by id.  Raises KeyError if not found.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Protocol

from lib.pattern_ops import (
    ElementNotFound,
    Pattern,
    element_bbox,
    get_element,
    piece_ids,
    render_pattern,
    scale_element,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Measurement protocol
# ---------------------------------------------------------------------------


class MeasurementsProtocol(Protocol):
    """Structural type for any object providing body measurements in centimetres.

    Compatible with lib.measurements.Measurements and any other dataclass or
    named tuple that exposes the four required float attributes.
    """

    bust_cm: float
    waist_cm: float
    hip_cm: float
    back_length_cm: float


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BaseMeasurements:
    """Base body measurements (cm) that a pattern is drafted for."""

    bust_cm: float
    waist_cm: float
    hip_cm: float
    back_length_cm: float


@dataclass(frozen=True)
class GradedPattern:
    """Result of grading a pattern to user measurements."""

    graded_pattern_id: str
    pattern_id: str
    measurement_id: str
    svg: str
    adjustments_cm: dict[str, float]


# ---------------------------------------------------------------------------
# In-memory session store
# ---------------------------------------------------------------------------

_store: dict[str, GradedPattern] = {}


def store_graded_pattern(g: GradedPattern) -> None:
    """Store a GradedPattern in the session store keyed by graded_pattern_id."""
    _store[g.graded_pattern_id] = g


def get_graded_pattern(graded_pattern_id: str) -> GradedPattern:
    """Retrieve a stored GradedPattern by id.  Raises KeyError if not found."""
    return _store[graded_pattern_id]


# ---------------------------------------------------------------------------
# Piece-to-measurement prefix mapping
# ---------------------------------------------------------------------------

# Prefixes that indicate a bodice piece (horizontal scale by bust ratio)
_BODICE_PREFIXES = ("bodice-", "front-bodice", "back-bodice")

# Prefixes that indicate a lower (skirt / hip) piece
_LOWER_PREFIXES = ("skirt-", "lower-")


def _horizontal_scale_for_piece(
    piece_id: str,
    sx_bust: float,
    sx_hip: float,
) -> float:
    """Return the horizontal scale factor for a piece based on its id prefix."""
    for prefix in _BODICE_PREFIXES:
        if piece_id.startswith(prefix):
            return sx_bust
    for prefix in _LOWER_PREFIXES:
        if piece_id.startswith(prefix):
            return sx_hip
    logger.warning(
        "piece id %r has no recognised prefix; applying sx=1.0 (no horizontal grade)",
        piece_id,
    )
    return 1.0


# ---------------------------------------------------------------------------
# Core grading logic
# ---------------------------------------------------------------------------


def grade_pattern(
    pattern: Pattern,
    base_measurements: BaseMeasurements,
    user_measurements: MeasurementsProtocol,
    pattern_id: str,
    measurement_id: str,
) -> GradedPattern:
    """Scale a pattern to user measurements; return a new GradedPattern.

    ``user_measurements`` must have attributes bust_cm, waist_cm, hip_cm,
    back_length_cm (compatible with lib.measurements.Measurements).

    The input pattern is never mutated — a deep copy is produced per piece scale.

    Piece scaling rules:
    - id prefix bodice-, front-bodice, back-bodice → sx = user.bust / base.bust
    - id prefix skirt-, lower-                     → sx = user.hip  / base.hip
    - anything else                                → sx = 1.0 (warn)
    - ALL pieces                                   → sy = user.back_length / base.back_length
    - Pivot = bounding-box centre of each piece's current geometry.

    adjustments_cm:
    - bust:        round(user.bust_cm - base.bust_cm, 1)
    - waist:       round(user.waist_cm - base.waist_cm, 1)
    - hip:         round(user.hip_cm - base.hip_cm, 1)
    - back_length: round(user.back_length_cm - base.back_length_cm, 1)
    """
    sx_bust = user_measurements.bust_cm / base_measurements.bust_cm
    sx_hip = user_measurements.hip_cm / base_measurements.hip_cm
    sy = user_measurements.back_length_cm / base_measurements.back_length_cm

    adjustments_cm = {
        "bust": round(user_measurements.bust_cm - base_measurements.bust_cm, 1),
        "waist": round(user_measurements.waist_cm - base_measurements.waist_cm, 1),
        "hip": round(user_measurements.hip_cm - base_measurements.hip_cm, 1),
        "back_length": round(
            user_measurements.back_length_cm - base_measurements.back_length_cm, 1
        ),
    }

    ids = piece_ids(pattern)
    current_pattern = pattern

    for piece_id in ids:
        sx = _horizontal_scale_for_piece(piece_id, sx_bust, sx_hip)

        # Compute pivot as bounding-box centre of the piece in current_pattern
        try:
            el = get_element(current_pattern, piece_id)
            bbox = element_bbox(el)
        except ElementNotFound:
            bbox = None
        if bbox is None:
            logger.warning("piece %r has no geometry; skipping grade", piece_id)
            continue

        min_x, min_y, max_x, max_y = bbox
        pivot = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)

        current_pattern = scale_element(current_pattern, piece_id, sx, sy, pivot)

    graded_svg = render_pattern(current_pattern)

    return GradedPattern(
        graded_pattern_id=str(uuid.uuid4()),
        pattern_id=pattern_id,
        measurement_id=measurement_id,
        svg=graded_svg,
        adjustments_cm=adjustments_cm,
    )
