"""Shared geometric constants for bodice-v1 cascade operations.

All values are in SVG user units. PX_PER_CM defines the physical scale:
1 cm in the real world = PX_PER_CM SVG units.
"""

PX_PER_CM: float = 5.0  # 1 cm = 10 mm × 0.5 px/mm
SCALE: float = PX_PER_CM * 2  # same as 10 * 0.5

# Bodice-v1 geometry constants — tied to the current viewBox geometry
CB_X: float = 210  # x-coordinate of centre-back seam
SIDE_SEAM_X: float = 390  # x-coordinate of back side seam
WAIST_Y: float = 160  # y-coordinate of waist line
