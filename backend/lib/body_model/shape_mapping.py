"""SMPL-X shape parameter (β) mapping from body measurements.

Linear approximation only — not full SMPL fitting. Used for rough visual
scaling of the 3D body to the user's measurements.
"""

from __future__ import annotations

from lib.measurements import MeasurementsResponse

# Reference measurements (SMPL neutral model baseline)
_REF_BUST_CM = 92.0
_REF_WAIST_CM = 76.0
_REF_HIP_CM = 100.0
_REF_HEIGHT_CM = 168.0

# Scale denominators per β component
_SCALE_BUST = 20.0
_SCALE_WAIST = 20.0
_SCALE_HIP = 20.0
_SCALE_HEIGHT = 10.0

_BETA_MIN = -3.0
_BETA_MAX = 3.0


def measurements_to_betas(m: MeasurementsResponse) -> list[float]:
    """Return a length-10 β vector for the SMPL neutral model.

    β[0] = (bust_cm   - 92)  / 20   (clamped to [-3, 3])
    β[1] = (waist_cm  - 76)  / 20   (clamped to [-3, 3])
    β[2] = (hip_cm    - 100) / 20   (clamped to [-3, 3])
    β[3] = (height_cm - 168) / 10   (clamped to [-3, 3])
    β[4..9] = 0.0
    """
    raw = [
        (m.bust_cm - _REF_BUST_CM) / _SCALE_BUST,
        (m.waist_cm - _REF_WAIST_CM) / _SCALE_WAIST,
        (m.hip_cm - _REF_HIP_CM) / _SCALE_HIP,
        (m.height_cm - _REF_HEIGHT_CM) / _SCALE_HEIGHT,
    ]
    clamped = [max(_BETA_MIN, min(_BETA_MAX, b)) for b in raw]
    return clamped + [0.0] * 6
