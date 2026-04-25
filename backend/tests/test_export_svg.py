"""Tests for lib/export/svg_export.py — spec 17-pattern-download.

Covers AC:
- build_svg_download returns (svg_string, "muslin-pattern.svg")
- lib/export/ has no fastapi imports (import hygiene)
"""

from __future__ import annotations

import ast
from pathlib import Path

from lib.grading import GradedPattern

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 400">
  <g id="bodice-front"><rect x="10" y="10" width="80" height="100"/></g>
</svg>"""

SAMPLE_GRADED = GradedPattern(
    graded_pattern_id="test-gp-svg-001",
    pattern_id="bodice-v1",
    measurement_id="test-m-001",
    svg=SAMPLE_SVG,
    adjustments_cm={"bust": 2.0, "waist": 1.0, "hip": 3.0, "back_length": 0.5},
)


# ---------------------------------------------------------------------------
# SVG download tests
# ---------------------------------------------------------------------------


class TestBuildSvgDownload:
    """AC: build_svg_download(graded) → (svg_string, filename)."""

    def test_returns_exact_svg_string(self) -> None:
        from lib.export.svg_export import build_svg_download

        svg, _ = build_svg_download(SAMPLE_GRADED)
        assert svg == SAMPLE_SVG

    def test_returns_correct_filename(self) -> None:
        from lib.export.svg_export import build_svg_download

        _, filename = build_svg_download(SAMPLE_GRADED)
        assert filename == "muslin-pattern.svg"

    def test_does_not_mutate_graded_pattern(self) -> None:
        from lib.export.svg_export import build_svg_download

        original_svg = SAMPLE_GRADED.svg
        build_svg_download(SAMPLE_GRADED)
        assert SAMPLE_GRADED.svg == original_svg


# ---------------------------------------------------------------------------
# Import hygiene
# ---------------------------------------------------------------------------


class TestImportHygiene:
    """AC: lib/export/ contains no fastapi imports."""

    def test_no_fastapi_imports_in_export_package(self) -> None:
        export_dir = Path(__file__).parent.parent / "lib" / "export"
        forbidden = {"fastapi", "starlette"}
        violations: list[str] = []

        for py_file in export_dir.rglob("*.py"):
            source = py_file.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(alias.name.startswith(f) for f in forbidden):
                            violations.append(f"{py_file.name}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    if any(module.startswith(f) for f in forbidden):
                        violations.append(f"{py_file.name}: from {module} import ...")

        assert not violations, f"Forbidden imports found: {violations}"
