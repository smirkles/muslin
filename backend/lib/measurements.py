"""Pure-logic models and helpers for body measurements.

No FastAPI imports — this module must be unit-testable in isolation.
"""

from pydantic import BaseModel, Field


class Measurements(BaseModel):
    """Validated body measurements in centimetres."""

    bust_cm: float = Field(..., ge=60, le=200)
    waist_cm: float = Field(..., ge=40, le=200)
    hip_cm: float = Field(..., ge=60, le=200)
    height_cm: float = Field(..., ge=120, le=220)
    back_length_cm: float = Field(..., ge=30, le=60)


class MeasurementsResponse(Measurements):
    """Validated measurements plus a derived standard size label."""

    size_label: str


def derive_size_label(bust_cm: float) -> str:
    """Return a British/Australian standard size label for the given bust measurement.

    Size table (bust in cm):
        < 83    → "8"
        83–87   → "10"
        88–92   → "12"
        93–97   → "14"
        98–102  → "16"
        103–107 → "18"
        108–112 → "20"
        113–117 → "22W"
        118–122 → "24W"
        ≥ 123   → "26W+"
    """
    if bust_cm < 83:
        return "8"
    if bust_cm <= 87:
        return "10"
    if bust_cm <= 92:
        return "12"
    if bust_cm <= 97:
        return "14"
    if bust_cm <= 102:
        return "16"
    if bust_cm <= 107:
        return "18"
    if bust_cm <= 112:
        return "20"
    if bust_cm <= 117:
        return "22W"
    if bust_cm <= 122:
        return "24W"
    return "26W+"
