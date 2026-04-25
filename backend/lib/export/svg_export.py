"""SVG download export for graded patterns.

No FastAPI imports — this module is pure logic.
"""

from __future__ import annotations

from lib.grading import GradedPattern


def build_svg_download(graded: GradedPattern) -> tuple[str, str]:
    """Return (svg_string, filename) for a graded pattern SVG download."""
    return graded.svg, "muslin-pattern.svg"
