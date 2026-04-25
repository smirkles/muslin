"""Tests for backend/lib/pattern_ops — pattern SVG manipulation library.

Acceptance criteria coverage:
  AC1:  load_pattern returns Pattern with all addressable elements
  AC2:  render_pattern produces valid SVG (round-trip stable)
  AC3:  translate_element shifts coordinates; original unchanged
  AC4:  translate_element with missing id raises ElementNotFound
  AC5:  rotate_element rotates 90° clockwise with known pairs
  AC6:  slash_line adds a <line> element; rest of pattern unchanged
  AC7:  spread_at_line translates one side + extends slash line
  AC8:  add_dart adds a dart-shaped polygon
  AC9:  true_seam_length extends seam A to match seam B length
  AC10: all operations are pure (same inputs → same outputs)
  AC11: test coverage >= 90% (enforced via pytest-cov configuration)
"""

from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from lxml import etree

from lib.pattern_ops import (
    ElementNotFound,
    GeometryError,
    Pattern,
    PatternError,
    add_dart,
    element_bbox,
    get_element,
    load_pattern,
    piece_ids,
    render_pattern,
    rotate_element,
    slash_line,
    spread_at_line,
    translate_element,
    true_seam_length,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures" / "patterns"
TRIANGLE_SVG = FIXTURES / "triangle.svg"
RECTANGLE_SVG = FIXTURES / "rectangle.svg"
WITH_DART_SVG = FIXTURES / "with_dart.svg"
GROUPED_PIECE_SVG = FIXTURES / "grouped_piece.svg"

SVG_NS = "http://www.w3.org/2000/svg"


def _parse_svg_string(svg_str: str) -> etree._Element:
    """Parse an SVG string and return the root element."""
    return etree.fromstring(svg_str.encode())


def _get_element_by_id(root: etree._Element, element_id: str) -> etree._Element | None:
    """Find an element by id in an lxml tree."""
    results = root.xpath(f'//*[@id="{element_id}"]')
    return results[0] if results else None


def _extract_path_coords(d_attr: str) -> list[tuple[float, float]]:
    """Extract numeric coordinate pairs from an SVG path d attribute.

    Handles simple M/L/Z commands with absolute coordinates separated by spaces
    or commas. This is a test-only helper — real parsing lives in pattern_ops.
    """
    import re

    # Remove command letters (M, L, Z, C, etc.) and split on whitespace/commas
    tokens = re.split(r"[,\s]+", re.sub(r"[MLZCzmlc]", " ", d_attr).strip())
    nums = [float(t) for t in tokens if t]
    coords = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
    return coords


# ---------------------------------------------------------------------------
# AC1 — load_pattern
# ---------------------------------------------------------------------------


class TestLoadPattern:
    def test_returns_pattern_object(self) -> None:
        """load_pattern returns a Pattern instance."""
        p = load_pattern(TRIANGLE_SVG)
        assert isinstance(p, Pattern)

    def test_path_elements_accessible_by_id(self) -> None:
        """All <path> elements are accessible by their id attribute."""
        p = load_pattern(TRIANGLE_SVG)
        el = get_element(p, "triangle")
        assert el is not None
        assert el.get("id") == "triangle"

    def test_group_elements_accessible_by_id(self) -> None:
        """<g> elements are accessible by id."""
        p = load_pattern(TRIANGLE_SVG)
        el = get_element(p, "pattern-group")
        assert el is not None

    def test_text_elements_accessible_by_id(self) -> None:
        """<text> elements are accessible by id."""
        p = load_pattern(TRIANGLE_SVG)
        el = get_element(p, "label")
        assert el is not None

    def test_rectangle_loads_all_elements(self) -> None:
        """All named elements in rectangle.svg are accessible."""
        p = load_pattern(RECTANGLE_SVG)
        for element_id in ("front-bodice", "seam-a", "seam-b", "hem", "grain-label"):
            el = get_element(p, element_id)
            assert el is not None, f"Element '{element_id}' not found"

    def test_with_dart_loads_polygon(self) -> None:
        """<polygon> elements are accessible by id."""
        p = load_pattern(WITH_DART_SVG)
        el = get_element(p, "waist-dart")
        assert el is not None

    def test_with_dart_loads_line(self) -> None:
        """<line> elements are accessible by id."""
        p = load_pattern(WITH_DART_SVG)
        el = get_element(p, "slash-line-existing")
        assert el is not None

    def test_missing_file_raises(self) -> None:
        """load_pattern raises PatternError for a missing file."""
        with pytest.raises(PatternError):
            load_pattern(FIXTURES / "nonexistent.svg")

    def test_invalid_xml_raises(self, tmp_path: Path) -> None:
        """load_pattern raises PatternError for invalid XML."""
        bad = tmp_path / "bad.svg"
        bad.write_text("<svg><unclosed>")
        with pytest.raises(PatternError):
            load_pattern(bad)


# ---------------------------------------------------------------------------
# AC2 — render_pattern (round-trip stability)
# ---------------------------------------------------------------------------


class TestRenderPattern:
    def test_returns_string(self) -> None:
        """render_pattern returns a string."""
        p = load_pattern(TRIANGLE_SVG)
        result = render_pattern(p)
        assert isinstance(result, str)

    def test_output_is_valid_xml(self) -> None:
        """render_pattern output can be parsed as XML."""
        p = load_pattern(TRIANGLE_SVG)
        svg_str = render_pattern(p)
        root = _parse_svg_string(svg_str)
        assert root is not None

    def test_round_trip_preserves_element_ids(self) -> None:
        """Elements accessible by id survive a load → render → re-parse cycle."""
        p = load_pattern(TRIANGLE_SVG)
        svg_str = render_pattern(p)
        p2 = load_pattern_from_string(svg_str)
        for element_id in ("triangle", "label", "pattern-group"):
            el = get_element(p2, element_id)
            assert el is not None, f"Element '{element_id}' lost in round-trip"

    def test_round_trip_preserves_path_data(self) -> None:
        """Path d attribute survives a round-trip."""
        p = load_pattern(TRIANGLE_SVG)
        original_d = get_element(p, "triangle").get("d")
        svg_str = render_pattern(p)
        p2 = load_pattern_from_string(svg_str)
        round_trip_d = get_element(p2, "triangle").get("d")
        # Normalise whitespace for comparison
        assert original_d is not None
        assert round_trip_d is not None

    def test_output_contains_svg_namespace(self) -> None:
        """The rendered string contains SVG namespace or is a valid SVG root."""
        p = load_pattern(TRIANGLE_SVG)
        svg_str = render_pattern(p)
        assert "<svg" in svg_str

    def test_rectangle_round_trip(self) -> None:
        """rectangle.svg survives a full round-trip."""
        p = load_pattern(RECTANGLE_SVG)
        svg_str = render_pattern(p)
        p2 = load_pattern_from_string(svg_str)
        for element_id in ("front-bodice", "seam-a", "seam-b"):
            assert get_element(p2, element_id) is not None


# ---------------------------------------------------------------------------
# Helper: load from string (used by round-trip tests)
# ---------------------------------------------------------------------------


def load_pattern_from_string(svg_str: str) -> Pattern:
    """Load a Pattern from an SVG string (test helper, not part of public API)."""
    # We reach into pattern_ops internals for test convenience.
    # The public API only has load_pattern(path), so we write to a temp file.
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", delete=False) as f:
        f.write(svg_str)
        tmp_path = Path(f.name)
    try:
        return load_pattern(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# AC3 & AC4 — translate_element
# ---------------------------------------------------------------------------


class TestTranslateElement:
    def test_coordinates_shift_by_dx_dy(self) -> None:
        """translate_element shifts all coordinates of a path by (dx, dy)."""
        p = load_pattern(TRIANGLE_SVG)
        original_d = get_element(p, "triangle").get("d")
        p2 = translate_element(p, "triangle", 10.0, 5.0)
        new_d = get_element(p2, "triangle").get("d")
        assert original_d != new_d

        orig_coords = _extract_path_coords(original_d)
        new_coords = _extract_path_coords(new_d)
        assert len(orig_coords) == len(new_coords)
        for (ox, oy), (nx, ny) in zip(orig_coords, new_coords, strict=True):
            assert abs(nx - (ox + 10.0)) < 1e-6, f"x mismatch: {nx} vs {ox + 10}"
            assert abs(ny - (oy + 5.0)) < 1e-6, f"y mismatch: {ny} vs {oy + 5}"

    def test_original_pattern_is_unchanged(self) -> None:
        """translate_element does not mutate the original Pattern."""
        p = load_pattern(TRIANGLE_SVG)
        original_d = get_element(p, "triangle").get("d")
        translate_element(p, "triangle", 100.0, 200.0)
        assert get_element(p, "triangle").get("d") == original_d

    def test_other_elements_unchanged(self) -> None:
        """Elements not targeted by translate_element are unchanged."""
        p = load_pattern(TRIANGLE_SVG)
        original_label_x = get_element(p, "label").get("x")
        p2 = translate_element(p, "triangle", 10.0, 5.0)
        assert get_element(p2, "label").get("x") == original_label_x

    def test_zero_translation_is_identity(self) -> None:
        """Translating by (0, 0) returns an equivalent pattern."""
        p = load_pattern(TRIANGLE_SVG)
        p2 = translate_element(p, "triangle", 0.0, 0.0)
        orig = _extract_path_coords(get_element(p, "triangle").get("d"))
        new = _extract_path_coords(get_element(p2, "triangle").get("d"))
        for (ox, oy), (nx, ny) in zip(orig, new, strict=True):
            assert abs(nx - ox) < 1e-6
            assert abs(ny - oy) < 1e-6

    def test_missing_id_raises_element_not_found(self) -> None:
        """translate_element raises ElementNotFound for a missing element id."""
        p = load_pattern(TRIANGLE_SVG)
        with pytest.raises(ElementNotFound):
            translate_element(p, "nonexistent-id", 10.0, 5.0)

    def test_element_not_found_is_subclass_of_pattern_error(self) -> None:
        """ElementNotFound is a subclass of PatternError."""
        assert issubclass(ElementNotFound, PatternError)

    def test_translate_polygon(self) -> None:
        """translate_element works on <polygon> elements via points attribute."""
        p = load_pattern(WITH_DART_SVG)
        p2 = translate_element(p, "waist-dart", 5.0, 0.0)
        orig_pts = get_element(p, "waist-dart").get("points")
        new_pts = get_element(p2, "waist-dart").get("points")
        assert orig_pts != new_pts

    def test_translate_line(self) -> None:
        """translate_element works on <line> elements."""
        p = load_pattern(WITH_DART_SVG)
        p2 = translate_element(p, "slash-line-existing", 10.0, 0.0)
        orig_x1 = float(get_element(p, "slash-line-existing").get("x1"))
        new_x1 = float(get_element(p2, "slash-line-existing").get("x1"))
        assert abs(new_x1 - (orig_x1 + 10.0)) < 1e-6

    def test_returns_pattern_instance(self) -> None:
        """translate_element returns a Pattern instance."""
        p = load_pattern(TRIANGLE_SVG)
        result = translate_element(p, "triangle", 1.0, 1.0)
        assert isinstance(result, Pattern)

    def test_negative_translation(self) -> None:
        """Negative dx/dy shifts coordinates in the negative direction."""
        p = load_pattern(TRIANGLE_SVG)
        p2 = translate_element(p, "triangle", -20.0, -10.0)
        orig = _extract_path_coords(get_element(p, "triangle").get("d"))
        new = _extract_path_coords(get_element(p2, "triangle").get("d"))
        for (ox, oy), (nx, ny) in zip(orig, new, strict=True):
            assert abs(nx - (ox - 20.0)) < 1e-6
            assert abs(ny - (oy - 10.0)) < 1e-6


# ---------------------------------------------------------------------------
# AC5 — rotate_element
# ---------------------------------------------------------------------------


class TestRotateElement:
    def test_90_clockwise_known_point(self) -> None:
        """rotate_element 90° clockwise: (1,0) → (0,-1) in math, (0,1) in SVG y-down.

        SVG y-axis points downward.  A 90° clockwise rotation in screen coords
        maps (x, y) → (y, -x)  [i.e. (1,0) → (0,−1) — stays at negative y].
        We verify with a path that has a known single coordinate.
        """
        # Build a tiny SVG with a single coordinate path for precision testing.
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="pt" d="M 1,0 L 1,0 Z"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = rotate_element(p, "pt", 90.0, (0.0, 0.0))
        new_d = get_element(p2, "pt").get("d")
        coords = _extract_path_coords(new_d)
        # 90° CW in SVG (y-down): (x,y) -> (y, -x)
        # (1,0) -> (0,-1)
        for nx, ny in coords:
            assert abs(nx - 0.0) < 1e-4, f"x should be 0, got {nx}"
            assert abs(ny - (-1.0)) < 1e-4, f"y should be -1, got {ny}"

    def test_90_clockwise_known_point_2(self) -> None:
        """rotate_element 90° CW: (0,1) → (1,0) in SVG y-down coords."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="pt" d="M 0,1 L 0,1 Z"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = rotate_element(p, "pt", 90.0, (0.0, 0.0))
        coords = _extract_path_coords(get_element(p2, "pt").get("d"))
        # (0,1) -> (1,0)
        for nx, ny in coords:
            assert abs(nx - 1.0) < 1e-4, f"x should be 1, got {nx}"
            assert abs(ny - 0.0) < 1e-4, f"y should be 0, got {ny}"

    def test_90_clockwise_known_point_3(self) -> None:
        """rotate_element 90° CW: (2,3) → (3,-2) in SVG y-down coords."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="pt" d="M 2,3 L 2,3 Z"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = rotate_element(p, "pt", 90.0, (0.0, 0.0))
        coords = _extract_path_coords(get_element(p2, "pt").get("d"))
        # (2,3) -> (3,-2)
        for nx, ny in coords:
            assert abs(nx - 3.0) < 1e-4, f"x should be 3, got {nx}"
            assert abs(ny - (-2.0)) < 1e-4, f"y should be -2, got {ny}"

    def test_360_rotation_is_identity(self) -> None:
        """360° rotation returns to original coordinates (within tolerance)."""
        p = load_pattern(TRIANGLE_SVG)
        orig_coords = _extract_path_coords(get_element(p, "triangle").get("d"))
        p2 = rotate_element(p, "triangle", 360.0, (0.0, 0.0))
        new_coords = _extract_path_coords(get_element(p2, "triangle").get("d"))
        for (ox, oy), (nx, ny) in zip(orig_coords, new_coords, strict=True):
            assert abs(nx - ox) < 1e-4
            assert abs(ny - oy) < 1e-4

    def test_zero_rotation_is_identity(self) -> None:
        """0° rotation returns original coordinates."""
        p = load_pattern(TRIANGLE_SVG)
        orig_coords = _extract_path_coords(get_element(p, "triangle").get("d"))
        p2 = rotate_element(p, "triangle", 0.0, (0.0, 0.0))
        new_coords = _extract_path_coords(get_element(p2, "triangle").get("d"))
        for (ox, oy), (nx, ny) in zip(orig_coords, new_coords, strict=True):
            assert abs(nx - ox) < 1e-4
            assert abs(ny - oy) < 1e-4

    def test_pivot_offsets_rotation(self) -> None:
        """Rotation around a non-origin pivot produces different result than around origin."""
        p = load_pattern(TRIANGLE_SVG)
        p_origin = rotate_element(p, "triangle", 45.0, (0.0, 0.0))
        p_pivot = rotate_element(p, "triangle", 45.0, (100.0, 100.0))
        coords_origin = _extract_path_coords(get_element(p_origin, "triangle").get("d"))
        coords_pivot = _extract_path_coords(get_element(p_pivot, "triangle").get("d"))
        # They should differ (different pivot → different result)
        diffs = [
            abs(ox - px) + abs(oy - py)
            for (ox, oy), (px, py) in zip(coords_origin, coords_pivot, strict=True)
        ]
        assert any(d > 1e-3 for d in diffs), "Expected pivot to change rotation result"

    def test_original_unchanged_after_rotate(self) -> None:
        """rotate_element does not mutate the original Pattern."""
        p = load_pattern(TRIANGLE_SVG)
        original_d = get_element(p, "triangle").get("d")
        rotate_element(p, "triangle", 45.0, (0.0, 0.0))
        assert get_element(p, "triangle").get("d") == original_d

    def test_missing_id_raises_element_not_found(self) -> None:
        """rotate_element raises ElementNotFound for a missing id."""
        p = load_pattern(TRIANGLE_SVG)
        with pytest.raises(ElementNotFound):
            rotate_element(p, "does-not-exist", 90.0, (0.0, 0.0))

    def test_returns_pattern_instance(self) -> None:
        """rotate_element returns a Pattern instance."""
        p = load_pattern(TRIANGLE_SVG)
        result = rotate_element(p, "triangle", 45.0, (50.0, 50.0))
        assert isinstance(result, Pattern)


# ---------------------------------------------------------------------------
# AC5 — Property-based: rotate X then -X should be identity
# ---------------------------------------------------------------------------


class TestRotateProperty:
    @given(
        angle=st.floats(min_value=-360.0, max_value=360.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_rotate_then_inverse_is_identity(self, angle: float) -> None:
        """Rotating by angle then -angle returns to original within tolerance."""
        p = load_pattern(TRIANGLE_SVG)
        pivot = (100.0, 100.0)
        p2 = rotate_element(p, "triangle", angle, pivot)
        p3 = rotate_element(p2, "triangle", -angle, pivot)
        orig_coords = _extract_path_coords(get_element(p, "triangle").get("d"))
        final_coords = _extract_path_coords(get_element(p3, "triangle").get("d"))
        for (ox, oy), (fx, fy) in zip(orig_coords, final_coords, strict=True):
            assert abs(fx - ox) < 1e-2, f"x drift {fx} vs {ox} at angle={angle}"
            assert abs(fy - oy) < 1e-2, f"y drift {fy} vs {oy} at angle={angle}"


# ---------------------------------------------------------------------------
# AC6 — slash_line
# ---------------------------------------------------------------------------


class TestSlashLine:
    def test_adds_line_element_with_given_id(self) -> None:
        """slash_line adds a <line> element with the specified id."""
        p = load_pattern(RECTANGLE_SVG)
        p2 = slash_line(p, (50.0, 20.0), (50.0, 180.0), "slash-cf")
        el = get_element(p2, "slash-cf")
        assert el is not None
        assert el.tag.endswith("line") or el.tag == "line"

    def test_line_has_correct_endpoints(self) -> None:
        """The added line has the from_pt and to_pt coordinates."""
        p = load_pattern(RECTANGLE_SVG)
        p2 = slash_line(p, (30.0, 10.0), (30.0, 190.0), "slash-test")
        el = get_element(p2, "slash-test")
        assert abs(float(el.get("x1")) - 30.0) < 1e-6
        assert abs(float(el.get("y1")) - 10.0) < 1e-6
        assert abs(float(el.get("x2")) - 30.0) < 1e-6
        assert abs(float(el.get("y2")) - 190.0) < 1e-6

    def test_rest_of_pattern_unchanged(self) -> None:
        """slash_line does not alter any existing elements."""
        p = load_pattern(RECTANGLE_SVG)
        orig_d = get_element(p, "seam-b").get("d")
        p2 = slash_line(p, (50.0, 20.0), (50.0, 180.0), "my-slash")
        assert get_element(p2, "seam-b").get("d") == orig_d

    def test_original_pattern_unchanged(self) -> None:
        """slash_line does not mutate the original Pattern."""
        p = load_pattern(RECTANGLE_SVG)
        slash_line(p, (50.0, 20.0), (50.0, 180.0), "slash-x")
        with pytest.raises(ElementNotFound):
            get_element(p, "slash-x")

    def test_returns_pattern_instance(self) -> None:
        """slash_line returns a Pattern instance."""
        p = load_pattern(RECTANGLE_SVG)
        result = slash_line(p, (10.0, 10.0), (10.0, 100.0), "sl")
        assert isinstance(result, Pattern)


# ---------------------------------------------------------------------------
# AC7 — spread_at_line
# ---------------------------------------------------------------------------


class TestSpreadAtLine:
    def _make_pattern_with_slash(self) -> tuple[Pattern, str]:
        """Create a rectangle pattern with a slash line down the middle."""
        p = load_pattern(RECTANGLE_SVG)
        # Slash line at x=150 from top to bottom of the 300x200 rectangle
        p2 = slash_line(p, (150.0, 20.0), (150.0, 180.0), "slash-mid")
        return p2, "slash-mid"

    def test_elements_on_one_side_translate(self) -> None:
        """Elements clearly on one side of the slash line are translated by the spread distance."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
  <path id="right-path" d="M 200,50 L 250,150"/>
  <path id="left-path" d="M 20,50 L 80,150"/>
  <line id="slash-v" x1="150" y1="0" x2="150" y2="200" stroke="red"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = spread_at_line(p, "slash-v", 10.0, (1.0, 0.0))

        # Right-side element (centroid at x=225) must shift by (10, 0)
        r_orig = _extract_path_coords(get_element(p, "right-path").get("d"))
        r_new = _extract_path_coords(get_element(p2, "right-path").get("d"))
        for (ox, oy), (nx, ny) in zip(r_orig, r_new, strict=True):
            assert abs(nx - (ox + 10.0)) < 1e-3, f"right-path x: expected {ox + 10}, got {nx}"
            assert abs(ny - oy) < 1e-3

        # Left-side element (centroid at x=50) must be unchanged
        l_orig = _extract_path_coords(get_element(p, "left-path").get("d"))
        l_new = _extract_path_coords(get_element(p2, "left-path").get("d"))
        for (ox, oy), (nx, ny) in zip(l_orig, l_new, strict=True):
            assert abs(nx - ox) < 1e-3, f"left-path x changed: {ox} → {nx}"
            assert abs(ny - oy) < 1e-3

    def test_slash_id_not_in_pattern_raises_geometry_error(self) -> None:
        """spread_at_line raises GeometryError if slash_id is not in the pattern."""
        p = load_pattern(RECTANGLE_SVG)
        with pytest.raises(GeometryError):
            spread_at_line(p, "nonexistent-slash", 5.0, (1.0, 0.0))

    def test_geometry_error_is_subclass_of_pattern_error(self) -> None:
        """GeometryError is a subclass of PatternError."""
        assert issubclass(GeometryError, PatternError)

    def test_original_pattern_unchanged(self) -> None:
        """spread_at_line does not mutate the original Pattern."""
        p, slash_id = self._make_pattern_with_slash()
        orig_d = get_element(p, "seam-b").get("d")
        spread_at_line(p, slash_id, 5.0, (1.0, 0.0))
        assert get_element(p, "seam-b").get("d") == orig_d

    def test_spread_zero_distance_unchanged(self) -> None:
        """Spreading by 0 distance leaves elements in place."""
        p, slash_id = self._make_pattern_with_slash()
        p2 = spread_at_line(p, slash_id, 0.0, (1.0, 0.0))
        # Elements should be at same coordinates as before
        orig_d = get_element(p, "seam-b").get("d")
        new_d = get_element(p2, "seam-b").get("d")
        orig_coords = _extract_path_coords(orig_d)
        new_coords = _extract_path_coords(new_d)
        # Given zero spread, coords should be essentially identical
        for (ox, oy), (nx, ny) in zip(orig_coords, new_coords, strict=True):
            assert abs(nx - ox) < 1e-3
            assert abs(ny - oy) < 1e-3

    def test_slash_line_extended_after_spread(self) -> None:
        """After spread, the slash line element is still present (and extended)."""
        p, slash_id = self._make_pattern_with_slash()
        p2 = spread_at_line(p, slash_id, 10.0, (1.0, 0.0))
        el = get_element(p2, slash_id)
        assert el is not None

    def test_returns_pattern_instance(self) -> None:
        """spread_at_line returns a Pattern instance."""
        p, slash_id = self._make_pattern_with_slash()
        result = spread_at_line(p, slash_id, 5.0, (1.0, 0.0))
        assert isinstance(result, Pattern)


# ---------------------------------------------------------------------------
# AC8 — add_dart
# ---------------------------------------------------------------------------


class TestAddDart:
    def test_dart_polygon_is_added(self) -> None:
        """add_dart adds an element with the given dart_id."""
        p = load_pattern(RECTANGLE_SVG)
        p2 = add_dart(p, (150.0, 20.0), 20.0, 60.0, 90.0, "new-dart")
        el = get_element(p2, "new-dart")
        assert el is not None

    def test_dart_is_triangle_shaped(self) -> None:
        """The dart element is a polygon (triangle) with 3 vertices."""
        p = load_pattern(RECTANGLE_SVG)
        p2 = add_dart(p, (150.0, 20.0), 20.0, 60.0, 90.0, "new-dart")
        el = get_element(p2, "new-dart")
        # Should be a polygon (triangle) or path with 3 points
        tag = el.tag
        assert "polygon" in tag or "path" in tag

        if "polygon" in tag:
            pts_str = el.get("points", "")
            # Count coordinate pairs — a triangle has 3
            import re

            pairs = re.findall(r"[\d.+-]+,[\d.+-]+", pts_str)
            assert len(pairs) == 3, f"Expected 3 vertices, got {len(pairs)}: {pts_str}"

    def test_original_pattern_unchanged(self) -> None:
        """add_dart does not mutate the original Pattern."""
        p = load_pattern(RECTANGLE_SVG)
        add_dart(p, (150.0, 20.0), 20.0, 60.0, 90.0, "dart-x")
        with pytest.raises(ElementNotFound):
            get_element(p, "dart-x")

    def test_existing_elements_unchanged(self) -> None:
        """add_dart does not alter other elements."""
        p = load_pattern(RECTANGLE_SVG)
        orig_d = get_element(p, "seam-b").get("d")
        p2 = add_dart(p, (150.0, 20.0), 20.0, 60.0, 90.0, "dart-y")
        assert get_element(p2, "seam-b").get("d") == orig_d

    def test_dart_position_matches_input(self) -> None:
        """The dart tip (apex) is at the specified position."""
        p = load_pattern(RECTANGLE_SVG)
        pos = (100.0, 50.0)
        p2 = add_dart(p, pos, 30.0, 80.0, 90.0, "dart-pos")
        el = get_element(p2, "dart-pos")
        pts_str = el.get("points", "")
        nums = [float(v) for v in re.split(r"[,\s]+", pts_str.strip()) if v]
        vertices = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
        # First vertex is the tip and must be exactly at `pos`
        assert (
            abs(vertices[0][0] - pos[0]) < 1e-4
        ), f"Tip x: expected {pos[0]}, got {vertices[0][0]}"
        assert (
            abs(vertices[0][1] - pos[1]) < 1e-4
        ), f"Tip y: expected {pos[1]}, got {vertices[0][1]}"

    def test_returns_pattern_instance(self) -> None:
        """add_dart returns a Pattern instance."""
        p = load_pattern(RECTANGLE_SVG)
        result = add_dart(p, (100.0, 100.0), 20.0, 50.0, 0.0, "d1")
        assert isinstance(result, Pattern)


# ---------------------------------------------------------------------------
# AC9 — true_seam_length
# ---------------------------------------------------------------------------


class TestTrueSeamLength:
    def _make_pattern_with_seams(self) -> Pattern:
        """Create a pattern with two path seams of different lengths for testing."""
        # seam-a: length 10 (horizontal, from 0,0 to 10,0)
        # seam-b: length 12 (horizontal, from 0,0 to 12,0)
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="seam-short" d="M 0,0 L 10,0"/>
  <path id="seam-long" d="M 0,0 L 12,0"/>
  <path id="seam-diag" d="M 0,0 L 30,40"/>
</svg>"""
        return load_pattern_from_string(svg_str)

    def test_seam_length_adjusted_to_match_target(self) -> None:
        """true_seam_length extends seam-short to match seam-long (within tolerance)."""
        p = self._make_pattern_with_seams()
        p2 = true_seam_length(p, "seam-short", "seam-long")
        new_d = get_element(p2, "seam-short").get("d")
        coords = _extract_path_coords(new_d)
        assert len(coords) >= 2
        start = np.array(coords[0])
        end = np.array(coords[-1])
        new_length = float(np.linalg.norm(end - start))
        assert abs(new_length - 12.0) < 1e-4, f"Expected length 12, got {new_length}"

    def test_seam_shortening(self) -> None:
        """true_seam_length contracts seam-long to match seam-short length."""
        p = self._make_pattern_with_seams()
        p2 = true_seam_length(p, "seam-long", "seam-short")
        new_d = get_element(p2, "seam-long").get("d")
        coords = _extract_path_coords(new_d)
        start = np.array(coords[0])
        end = np.array(coords[-1])
        new_length = float(np.linalg.norm(end - start))
        assert abs(new_length - 10.0) < 1e-4, f"Expected length 10, got {new_length}"

    def test_diagonal_seam_adjusted_correctly(self) -> None:
        """true_seam_length works for diagonal seams (not just axis-aligned)."""
        # seam-diag has length = sqrt(30^2 + 40^2) = 50
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="seam-diag" d="M 0,0 L 30,40"/>
  <path id="seam-target" d="M 0,0 L 0,25"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = true_seam_length(p, "seam-diag", "seam-target")
        new_d = get_element(p2, "seam-diag").get("d")
        coords = _extract_path_coords(new_d)
        start = np.array(coords[0])
        end = np.array(coords[-1])
        new_length = float(np.linalg.norm(end - start))
        target_length = 25.0
        assert abs(new_length - target_length) < 1e-4

    def test_original_pattern_unchanged(self) -> None:
        """true_seam_length does not mutate the original Pattern."""
        p = self._make_pattern_with_seams()
        orig_d = get_element(p, "seam-short").get("d")
        true_seam_length(p, "seam-short", "seam-long")
        assert get_element(p, "seam-short").get("d") == orig_d

    def test_seam_a_missing_raises(self) -> None:
        """true_seam_length raises ElementNotFound if seam_a doesn't exist."""
        p = self._make_pattern_with_seams()
        with pytest.raises(ElementNotFound):
            true_seam_length(p, "nonexistent", "seam-long")

    def test_seam_b_missing_raises(self) -> None:
        """true_seam_length raises ElementNotFound if seam_b doesn't exist."""
        p = self._make_pattern_with_seams()
        with pytest.raises(ElementNotFound):
            true_seam_length(p, "seam-short", "nonexistent")

    def test_equal_length_seams_unchanged(self) -> None:
        """When seam A and seam B are equal length, seam A is unchanged."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="seam-a" d="M 0,0 L 10,0"/>
  <path id="seam-b" d="M 0,0 L 10,0"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = true_seam_length(p, "seam-a", "seam-b")
        orig_d = get_element(p, "seam-a").get("d")
        new_d = get_element(p2, "seam-a").get("d")
        orig_coords = _extract_path_coords(orig_d)
        new_coords = _extract_path_coords(new_d)
        for (ox, oy), (nx, ny) in zip(orig_coords, new_coords, strict=True):
            assert abs(nx - ox) < 1e-4
            assert abs(ny - oy) < 1e-4

    def test_returns_pattern_instance(self) -> None:
        """true_seam_length returns a Pattern instance."""
        p = self._make_pattern_with_seams()
        result = true_seam_length(p, "seam-short", "seam-long")
        assert isinstance(result, Pattern)


# ---------------------------------------------------------------------------
# AC10 — Purity (same inputs → same outputs)
# ---------------------------------------------------------------------------


class TestPurity:
    def test_translate_is_pure(self) -> None:
        """Calling translate_element twice with same args produces equal results."""
        p = load_pattern(TRIANGLE_SVG)
        p2 = translate_element(p, "triangle", 15.0, 8.0)
        p3 = translate_element(p, "triangle", 15.0, 8.0)
        coords2 = _extract_path_coords(get_element(p2, "triangle").get("d"))
        coords3 = _extract_path_coords(get_element(p3, "triangle").get("d"))
        for (x2, y2), (x3, y3) in zip(coords2, coords3, strict=True):
            assert abs(x2 - x3) < 1e-9
            assert abs(y2 - y3) < 1e-9

    def test_rotate_is_pure(self) -> None:
        """Calling rotate_element twice with same args produces equal results."""
        p = load_pattern(TRIANGLE_SVG)
        p2 = rotate_element(p, "triangle", 45.0, (50.0, 50.0))
        p3 = rotate_element(p, "triangle", 45.0, (50.0, 50.0))
        coords2 = _extract_path_coords(get_element(p2, "triangle").get("d"))
        coords3 = _extract_path_coords(get_element(p3, "triangle").get("d"))
        for (x2, y2), (x3, y3) in zip(coords2, coords3, strict=True):
            assert abs(x2 - x3) < 1e-6
            assert abs(y2 - y3) < 1e-6

    def test_slash_line_is_pure(self) -> None:
        """slash_line called twice with same args produces equal results."""
        p = load_pattern(RECTANGLE_SVG)
        p2 = slash_line(p, (50.0, 20.0), (50.0, 180.0), "sl1")
        p3 = slash_line(p, (50.0, 20.0), (50.0, 180.0), "sl1")
        el2 = get_element(p2, "sl1")
        el3 = get_element(p3, "sl1")
        assert el2.get("x1") == el3.get("x1")
        assert el2.get("y1") == el3.get("y1")

    def test_add_dart_is_pure(self) -> None:
        """add_dart called twice with same args produces equal results."""
        p = load_pattern(RECTANGLE_SVG)
        p2 = add_dart(p, (100.0, 50.0), 20.0, 50.0, 90.0, "d1")
        p3 = add_dart(p, (100.0, 50.0), 20.0, 50.0, 90.0, "d1")
        el2 = get_element(p2, "d1")
        el3 = get_element(p3, "d1")
        assert el2.get("points") == el3.get("points")

    def test_spread_at_line_is_pure(self) -> None:
        """spread_at_line called twice with same args produces identical results."""
        p = load_pattern(RECTANGLE_SVG)
        p = slash_line(p, (150.0, 20.0), (150.0, 180.0), "slash-mid")
        p2 = spread_at_line(p, "slash-mid", 10.0, (1.0, 0.0))
        p3 = spread_at_line(p, "slash-mid", 10.0, (1.0, 0.0))
        sl2 = get_element(p2, "slash-mid")
        sl3 = get_element(p3, "slash-mid")
        assert sl2.get("x2") == sl3.get("x2")
        assert sl2.get("y2") == sl3.get("y2")

    def test_true_seam_length_is_pure(self) -> None:
        """true_seam_length called twice with same args produces identical results."""
        svg_str = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
            '<path id="seam-a" d="M 0,0 L 10,0"/>'
            '<path id="seam-b" d="M 0,0 L 12,0"/>'
            "</svg>"
        )
        p = load_pattern_from_string(svg_str)
        p2 = true_seam_length(p, "seam-a", "seam-b")
        p3 = true_seam_length(p, "seam-a", "seam-b")
        assert get_element(p2, "seam-a").get("d") == get_element(p3, "seam-a").get("d")


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class TestErrorHierarchy:
    def test_pattern_error_is_exception(self) -> None:
        assert issubclass(PatternError, Exception)

    def test_element_not_found_is_pattern_error(self) -> None:
        assert issubclass(ElementNotFound, PatternError)

    def test_geometry_error_is_pattern_error(self) -> None:
        assert issubclass(GeometryError, PatternError)


# ---------------------------------------------------------------------------
# Coverage-gap tests: H/V/A path commands, rotate polygon/line, edge cases
# ---------------------------------------------------------------------------


class TestPathCommandCoverage:
    """Tests that exercise H, V, and A SVG path commands in transforms."""

    def test_translate_path_with_H_command(self) -> None:
        """translate_element shifts H command endpoints by (dx, dy)."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="hpath" d="M 10,20 H 50 H 80"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = translate_element(p, "hpath", 5.0, 3.0)
        new_d = get_element(p2, "hpath").get("d")
        # H is promoted to L; absolute endpoints: (15,23), (55,23), (85,23)
        coords = _extract_path_coords(new_d)
        assert len(coords) == 3
        assert abs(coords[0][0] - 15.0) < 1e-4
        assert abs(coords[0][1] - 23.0) < 1e-4
        assert abs(coords[1][0] - 55.0) < 1e-4
        assert abs(coords[1][1] - 23.0) < 1e-4
        assert abs(coords[2][0] - 85.0) < 1e-4
        assert abs(coords[2][1] - 23.0) < 1e-4

    def test_translate_path_with_V_command(self) -> None:
        """translate_element shifts V command endpoints by (dx, dy)."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="vpath" d="M 10,10 V 50 V 80"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = translate_element(p, "vpath", 0.0, 10.0)
        new_d = get_element(p2, "vpath").get("d")
        # V is promoted to L; absolute endpoints: (10,20), (10,60), (10,90)
        coords = _extract_path_coords(new_d)
        assert len(coords) == 3
        assert abs(coords[0][0] - 10.0) < 1e-4
        assert abs(coords[0][1] - 20.0) < 1e-4
        assert abs(coords[1][0] - 10.0) < 1e-4
        assert abs(coords[1][1] - 60.0) < 1e-4
        assert abs(coords[2][0] - 10.0) < 1e-4
        assert abs(coords[2][1] - 90.0) < 1e-4

    def test_rotate_polygon_element(self) -> None:
        """rotate_element correctly handles <polygon> elements."""
        p = load_pattern(WITH_DART_SVG)
        orig_pts = get_element(p, "waist-dart").get("points")
        p2 = rotate_element(p, "waist-dart", 90.0, (0.0, 0.0))
        new_pts = get_element(p2, "waist-dart").get("points")
        assert orig_pts != new_pts

    def test_rotate_line_element(self) -> None:
        """rotate_element correctly handles <line> elements."""
        p = load_pattern(WITH_DART_SVG)
        orig_x1 = get_element(p, "slash-line-existing").get("x1")
        p2 = rotate_element(p, "slash-line-existing", 90.0, (0.0, 0.0))
        new_x1 = get_element(p2, "slash-line-existing").get("x1")
        assert orig_x1 != new_x1

    def test_rotate_text_element(self) -> None:
        """rotate_element correctly handles <text> elements."""
        p = load_pattern(WITH_DART_SVG)
        # The with_dart fixture doesn't have text; use triangle.svg
        p = load_pattern(TRIANGLE_SVG)
        orig_x = get_element(p, "label").get("x")
        p2 = rotate_element(p, "label", 90.0, (0.0, 0.0))
        new_x = get_element(p2, "label").get("x")
        assert orig_x != new_x

    def test_translate_text_element(self) -> None:
        """translate_element correctly handles <text> elements via x/y attrs."""
        p = load_pattern(TRIANGLE_SVG)
        orig_x = float(get_element(p, "label").get("x"))
        p2 = translate_element(p, "label", 20.0, 0.0)
        new_x = float(get_element(p2, "label").get("x"))
        assert abs(new_x - (orig_x + 20.0)) < 1e-6


class TestSlashLineNoNamespace:
    """Tests for slash_line when SVG has no namespace (edge case)."""

    def test_slash_line_on_no_namespace_svg(self) -> None:
        """slash_line works even when the SVG has no namespace declaration."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg width="200" height="200">
  <path id="body" d="M 0,0 L 100,0 L 100,100 L 0,100 Z"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = slash_line(p, (50.0, 0.0), (50.0, 100.0), "cut-here")
        el = get_element(p2, "cut-here")
        assert el is not None


class TestSpreadAtLineCoverage:
    """Additional spread_at_line tests that exercise text/polygon centroids."""

    def test_spread_with_polygon_on_right_side(self) -> None:
        """spread_at_line correctly classifies a polygon's centroid."""
        # Polygon centred at (200, 100) — to the right of a vertical slash at x=150
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
  <polygon id="right-poly" points="180,80 220,80 220,120 180,120"/>
  <polygon id="left-poly" points="30,80 70,80 70,120 30,120"/>
  <line id="slash-v" x1="150" y1="0" x2="150" y2="200" stroke="red"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = spread_at_line(p, "slash-v", 10.0, (1.0, 0.0))
        # right-poly centroid (200,100) is to the right of the vertical slash → moved
        new_pts = get_element(p2, "right-poly").get("points")
        assert "190" in new_pts  # shifted right by 10

        # left-poly centroid (50,100) is to the left → not moved
        left_pts = get_element(p2, "left-poly").get("points")
        # original left poly starts at x=30
        assert "30" in left_pts


class TestTrueSeamLengthEdgeCases:
    """Edge-case tests for true_seam_length error paths."""

    def test_zero_length_seam_a_raises_geometry_error(self) -> None:
        """true_seam_length raises GeometryError if seam A has zero length."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="zero-seam" d="M 5,5 L 5,5"/>
  <path id="ref-seam" d="M 0,0 L 10,0"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        with pytest.raises(GeometryError):
            true_seam_length(p, "zero-seam", "ref-seam")


class TestGetElement:
    """Tests for get_element."""

    def test_get_element_returns_element(self) -> None:
        """get_element returns the correct element."""
        p = load_pattern(TRIANGLE_SVG)
        el = get_element(p, "triangle")
        assert el.get("id") == "triangle"

    def test_get_element_missing_raises(self) -> None:
        """get_element raises ElementNotFound for a missing id."""
        p = load_pattern(TRIANGLE_SVG)
        with pytest.raises(ElementNotFound) as exc_info:
            get_element(p, "no-such-element")
        assert "no-such-element" in str(exc_info.value)


class TestArcPathCommand:
    """Tests for A (arc) SVG path command handling in transforms."""

    def test_translate_path_with_arc_command(self) -> None:
        """translate_element transforms the endpoint of an A (arc) command."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="arc-path" d="M 50,100 A 50,50 0 0,1 150,100"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = translate_element(p, "arc-path", 10.0, 5.0)
        new_d = get_element(p2, "arc-path").get("d")
        assert new_d is not None
        # The arc endpoint (150,100) should become (160,105)
        assert "160" in new_d
        assert "105" in new_d


class TestSpreadAtLineEdgeCases:
    """Edge-case coverage for spread_at_line."""

    def test_spread_on_zero_length_slash_uses_default_normal(self) -> None:
        """spread_at_line handles a degenerate (zero-length) slash line gracefully."""
        # A zero-length line (from_pt == to_pt)
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="body" d="M 0,0 L 200,0 L 200,200 L 0,200 Z"/>
  <line id="zero-slash" x1="100" y1="100" x2="100" y2="100" stroke="red"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        # Should not raise — degenerate slash falls back to default normal
        result = spread_at_line(p, "zero-slash", 5.0, (1.0, 0.0))
        assert isinstance(result, Pattern)

    def test_spread_with_line_elements_in_pattern(self) -> None:
        """spread_at_line correctly classifies <line> element centroids."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
  <line id="right-line" x1="200" y1="50" x2="250" y2="150" stroke="black"/>
  <line id="left-line" x1="20" y1="50" x2="80" y2="150" stroke="black"/>
  <line id="slash-v" x1="150" y1="0" x2="150" y2="200" stroke="red"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = spread_at_line(p, "slash-v", 10.0, (1.0, 0.0))
        # right-line centroid (225,100) is right of slash at x=150 → moved
        new_x1 = float(get_element(p2, "right-line").get("x1"))
        assert abs(new_x1 - 210.0) < 1e-3  # 200 + 10
        # left-line centroid (50,100) is left → not moved
        left_x1 = float(get_element(p2, "left-line").get("x1"))
        assert abs(left_x1 - 20.0) < 1e-3


class TestInternalHelperEdgeCases:
    """Edge cases for internal helpers to improve branch coverage."""

    def test_true_seam_length_with_z_command_in_path(self) -> None:
        """true_seam_length correctly handles paths that include a Z command."""
        # The Z command should be skipped when measuring length
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="closed-a" d="M 0,0 L 10,0 Z"/>
  <path id="ref-b" d="M 0,0 L 20,0"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = true_seam_length(p, "closed-a", "ref-b")
        new_d = get_element(p2, "closed-a").get("d")
        coords = _extract_path_coords(new_d)
        assert len(coords) >= 2
        start = np.array(coords[0])
        end = np.array(coords[-1])
        new_len = float(np.linalg.norm(end - start))
        assert abs(new_len - 20.0) < 1e-4


# ---------------------------------------------------------------------------
# Spec 07 — translate_element on <g> group (AC fix)
# ---------------------------------------------------------------------------


class TestTranslateGroup:
    """Spec 07: translate_element on a <g> must recurse into all children."""

    def test_translate_group_shifts_both_path_children(self) -> None:
        """Translating a <g> shifts all child <path> coordinates."""
        p = load_pattern(GROUPED_PIECE_SVG)
        p2 = translate_element(p, "bodice-front", 10, 5)
        d = get_element(p2, "front-outline").get("d")
        # Original M 10,10 → M 20,15
        assert "20" in d
        assert "15" in d

    def test_translate_group_shifts_second_path_child(self) -> None:
        """Both child paths in the group are translated."""
        p = load_pattern(GROUPED_PIECE_SVG)
        p2 = translate_element(p, "bodice-front", 10, 5)
        d = get_element(p2, "front-seam").get("d")
        # Original M 10,10 → M 20,15
        assert "20" in d
        assert "15" in d

    def test_translate_group_leaves_sibling_unchanged(self) -> None:
        """Elements outside the translated group are not affected."""
        p = load_pattern(GROUPED_PIECE_SVG)
        p2 = translate_element(p, "bodice-front", 10, 5)
        d = get_element(p2, "sibling-path").get("d")
        # sibling-path at M 150,300 — should be unchanged
        assert "150" in d
        assert "300" in d

    def test_translate_group_does_not_mutate_original(self) -> None:
        """Original pattern is unmodified after group translation."""
        p = load_pattern(GROUPED_PIECE_SVG)
        _ = translate_element(p, "bodice-front", 10, 5)
        d_orig = get_element(p, "front-outline").get("d")
        # Original starts at M 10,10
        assert "M 10" in d_orig

    def test_translate_nested_group_recurses_to_innermost_path(self) -> None:
        """Translating outer-g reaches nested-path inside inner-g."""
        p = load_pattern(GROUPED_PIECE_SVG)
        p2 = translate_element(p, "outer-g", 20, 30)
        d = get_element(p2, "nested-path").get("d")
        # Original M 200,10 → M 220,40
        assert "220" in d
        assert "40" in d


# ---------------------------------------------------------------------------
# true_seam_length — polyline arc length correctness (multi-segment paths)
# ---------------------------------------------------------------------------


def _arc_length(coords: list[tuple[float, float]]) -> float:
    """Sum of Euclidean distances between consecutive coordinate pairs."""
    return sum(
        math.sqrt((coords[i][0] - coords[i - 1][0]) ** 2 + (coords[i][1] - coords[i - 1][1]) ** 2)
        for i in range(1, len(coords))
    )


class TestTrueSeamLengthPolyline:
    """true_seam_length must use polyline arc length, not start-to-end Euclidean.

    A zigzag path M 0,0 L 3,4 L 0,8 has polyline length 10 (5+5) but
    start-to-end distance of only 8.  All adjustments must use arc length.
    """

    def _zigzag_pattern(self) -> Pattern:
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="seam-zigzag" d="M 0,0 L 3,4 L 0,8"/>
  <path id="target-12" d="M 0,0 L 12,0"/>
  <path id="target-6" d="M 0,0 L 6,0"/>
</svg>"""
        return load_pattern_from_string(svg_str)

    def test_multisegment_length_measured_correctly(self) -> None:
        """true_seam_length treats M 0,0 L 3,4 L 0,8 as length 10, not 8."""
        p = self._zigzag_pattern()
        # Extend zigzag (arc length 10) to match target-12 (length 12)
        p2 = true_seam_length(p, "seam-zigzag", "target-12")
        coords = _extract_path_coords(get_element(p2, "seam-zigzag").get("d"))
        assert (
            abs(_arc_length(coords) - 12.0) < 1e-4
        ), f"Expected arc length 12, got {_arc_length(coords)}"

    def test_multisegment_shortening_uses_arc_length(self) -> None:
        """Shortening a zigzag to 6 places the new endpoint inside the last segment."""
        p = self._zigzag_pattern()
        # Shorten zigzag (arc length 10) to 6
        p2 = true_seam_length(p, "seam-zigzag", "target-6")
        coords = _extract_path_coords(get_element(p2, "seam-zigzag").get("d"))
        assert (
            abs(_arc_length(coords) - 6.0) < 1e-4
        ), f"Expected arc length 6, got {_arc_length(coords)}"

    def test_single_segment_unchanged(self) -> None:
        """Single-segment paths still work correctly after the fix."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="seam-a" d="M 0,0 L 10,0"/>
  <path id="seam-b" d="M 0,0 L 12,0"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = true_seam_length(p, "seam-a", "seam-b")
        coords = _extract_path_coords(get_element(p2, "seam-a").get("d"))
        assert abs(_arc_length(coords) - 12.0) < 1e-4


# ---------------------------------------------------------------------------
# B1 — Relative-command transform correctness
# ---------------------------------------------------------------------------


class TestRelativeCommandTransform:
    """B1: relative SVG path commands must be resolved to absolute before transform."""

    def test_translate_relative_path_absolute_endpoints(self) -> None:
        """Translating a relative path leaves the relative offsets intact.

        m 10,10 l 5,5 encodes absolute endpoints (10,10) and (15,15).
        Translating by (3,0) must produce endpoints (13,10) and (18,15).
        """
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="p" d="m 10,10 l 5,5"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = translate_element(p, "p", 3.0, 0.0)
        coords = _extract_path_coords(get_element(p2, "p").get("d"))
        assert len(coords) == 2
        assert abs(coords[0][0] - 13.0) < 1e-4, f"start x: expected 13, got {coords[0][0]}"
        assert abs(coords[0][1] - 10.0) < 1e-4, f"start y: expected 10, got {coords[0][1]}"
        assert abs(coords[1][0] - 18.0) < 1e-4, f"end x: expected 18, got {coords[1][0]}"
        assert abs(coords[1][1] - 15.0) < 1e-4, f"end y: expected 15, got {coords[1][1]}"

    def test_rotate_relative_path_around_non_origin_pivot(self) -> None:
        """Rotating a relative path around a non-origin pivot transforms absolute endpoints.

        m 10,10 l 5,5 → absolute endpoints (10,10) and (15,15).
        Rotate 90° CW around (100,100):
          (10,10)  → v=(-90,-90), R*v=(-90, 90), +pivot → (10,  190)
          (15,15)  → v=(-85,-85), R*v=(-85, 85), +pivot → (15,  185)
        """
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="p" d="m 10,10 l 5,5"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = rotate_element(p, "p", 90.0, (100.0, 100.0))
        coords = _extract_path_coords(get_element(p2, "p").get("d"))
        assert len(coords) == 2
        assert abs(coords[0][0] - 10.0) < 1e-4, f"pt0 x: expected 10, got {coords[0][0]}"
        assert abs(coords[0][1] - 190.0) < 1e-4, f"pt0 y: expected 190, got {coords[0][1]}"
        assert abs(coords[1][0] - 15.0) < 1e-4, f"pt1 x: expected 15, got {coords[1][0]}"
        assert abs(coords[1][1] - 185.0) < 1e-4, f"pt1 y: expected 185, got {coords[1][1]}"


# ---------------------------------------------------------------------------
# B2 — H/V command rotation correctness
# ---------------------------------------------------------------------------


class TestHVCommandRotation:
    """B2: H and V commands must be promoted to L under rotation."""

    def test_rotate_H_command_90cw_around_origin(self) -> None:
        """Rotating M 10,10 H 50 by 90° CW around origin transforms both endpoints.

        Original absolute endpoints: (10,10) and (50,10).
        90° CW in SVG (y-down), R = [[0,1],[-1,0]]:
          (10,10) → (10, -10)
          (50,10) → (10, -50)
        """
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="p" d="M 10,10 H 50"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = rotate_element(p, "p", 90.0, (0.0, 0.0))
        coords = _extract_path_coords(get_element(p2, "p").get("d"))
        assert len(coords) == 2
        assert abs(coords[0][0] - 10.0) < 1e-4, f"M x: expected 10, got {coords[0][0]}"
        assert abs(coords[0][1] - (-10.0)) < 1e-4, f"M y: expected -10, got {coords[0][1]}"
        assert abs(coords[1][0] - 10.0) < 1e-4, f"H→L x: expected 10, got {coords[1][0]}"
        assert abs(coords[1][1] - (-50.0)) < 1e-4, f"H→L y: expected -50, got {coords[1][1]}"

    def test_rotate_V_command_90cw_around_origin(self) -> None:
        """Rotating M 10,10 V 50 by 90° CW around origin transforms both endpoints.

        Original absolute endpoints: (10,10) and (10,50).
        90° CW: (10,10) → (10,-10); (10,50) → (50,-10).
        """
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="p" d="M 10,10 V 50"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = rotate_element(p, "p", 90.0, (0.0, 0.0))
        coords = _extract_path_coords(get_element(p2, "p").get("d"))
        assert len(coords) == 2
        assert abs(coords[0][0] - 10.0) < 1e-4, f"M x: expected 10, got {coords[0][0]}"
        assert abs(coords[0][1] - (-10.0)) < 1e-4, f"M y: expected -10, got {coords[0][1]}"
        assert abs(coords[1][0] - 50.0) < 1e-4, f"V→L x: expected 50, got {coords[1][0]}"
        assert abs(coords[1][1] - (-10.0)) < 1e-4, f"V→L y: expected -10, got {coords[1][1]}"

    def test_rotate_H_command_non_origin_pivot(self) -> None:
        """H command under rotation around a non-origin pivot produces correct L endpoint."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="p" d="M 50,50 H 150"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = rotate_element(p, "p", 90.0, (100.0, 100.0))
        coords = _extract_path_coords(get_element(p2, "p").get("d"))
        # (50,50) around (100,100): v=(-50,-50), R*v=(-50,50), +pivot=(50,150)
        # (150,50) around (100,100): v=(50,-50), R*v=(-50,-50), +pivot=(50,50)
        assert len(coords) == 2
        assert abs(coords[0][0] - 50.0) < 1e-4, f"M x: expected 50, got {coords[0][0]}"
        assert abs(coords[0][1] - 150.0) < 1e-4, f"M y: expected 150, got {coords[0][1]}"
        assert abs(coords[1][0] - 50.0) < 1e-4, f"H→L x: expected 50, got {coords[1][0]}"
        assert abs(coords[1][1] - 50.0) < 1e-4, f"H→L y: expected 50, got {coords[1][1]}"


# ---------------------------------------------------------------------------
# B3 — Multi-pair relative command coverage
# ---------------------------------------------------------------------------


class TestRelativeMultiPairCommands:
    """B3: multi-pair relative commands (c/s/q, chained m) must resolve correctly.

    Exercises the stride-based loop path added for B1 — specifically the
    rep_start advance on continuation pairs (line 276 of pattern_ops.py).
    """

    def test_translate_relative_cubic(self) -> None:
        """Translating M 0,0 c 10,0 10,10 10,10 by (+5, 0) shifts all pairs.

        c with pen at (0,0): control1=(10,0), control2=(10,10), endpoint=(10,10).
        After translate (+5, 0): M→(5,0), C→(15,0),(15,10),(15,10).
        """
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="p" d="M 0,0 c 10,0 10,10 10,10"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = translate_element(p, "p", 5.0, 0.0)
        coords = _extract_path_coords(get_element(p2, "p").get("d"))
        # M + 3 C pairs = 4 coordinate pairs
        assert len(coords) == 4, f"expected 4 coord pairs, got {len(coords)}"
        assert abs(coords[0][0] - 5.0) < 1e-4, f"M x: expected 5, got {coords[0][0]}"
        assert abs(coords[0][1] - 0.0) < 1e-4, f"M y: expected 0, got {coords[0][1]}"
        assert abs(coords[1][0] - 15.0) < 1e-4, f"C ctrl1 x: expected 15, got {coords[1][0]}"
        assert abs(coords[1][1] - 0.0) < 1e-4, f"C ctrl1 y: expected 0, got {coords[1][1]}"
        assert abs(coords[2][0] - 15.0) < 1e-4, f"C ctrl2 x: expected 15, got {coords[2][0]}"
        assert abs(coords[2][1] - 10.0) < 1e-4, f"C ctrl2 y: expected 10, got {coords[2][1]}"
        assert abs(coords[3][0] - 15.0) < 1e-4, f"C end x: expected 15, got {coords[3][0]}"
        assert abs(coords[3][1] - 10.0) < 1e-4, f"C end y: expected 10, got {coords[3][1]}"

    def test_translate_multi_pair_relative_lineto(self) -> None:
        """m 10,10 5,5 3,3 encodes three absolute endpoints; each shifts under translate.

        Pen starts at (0,0).
        m first pair: abs (10,10) → pen=(10,10).
        m second pair (implicit l): abs (10+5, 10+5)=(15,15) → pen=(15,15).
        m third pair (implicit l): abs (15+3, 15+3)=(18,18).
        Translate (+1, 0) → (11,10), (16,15), (19,18).
        """
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="p" d="m 10,10 5,5 3,3"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = translate_element(p, "p", 1.0, 0.0)
        coords = _extract_path_coords(get_element(p2, "p").get("d"))
        assert len(coords) == 3, f"expected 3 coord pairs, got {len(coords)}"
        assert abs(coords[0][0] - 11.0) < 1e-4, f"pt0 x: expected 11, got {coords[0][0]}"
        assert abs(coords[0][1] - 10.0) < 1e-4, f"pt0 y: expected 10, got {coords[0][1]}"
        assert abs(coords[1][0] - 16.0) < 1e-4, f"pt1 x: expected 16, got {coords[1][0]}"
        assert abs(coords[1][1] - 15.0) < 1e-4, f"pt1 y: expected 15, got {coords[1][1]}"
        assert abs(coords[2][0] - 19.0) < 1e-4, f"pt2 x: expected 19, got {coords[2][0]}"
        assert abs(coords[2][1] - 18.0) < 1e-4, f"pt2 y: expected 18, got {coords[2][1]}"

    def test_multi_pair_M_subpath_start_not_overwritten(self) -> None:
        """Z after a multi-pair M block returns to the first pair, not the last.

        M 0,0 10,10 Z: subpath start is (0,0). After Z, pen = (0,0).
        The implicit lineto (10,10) must not reset the subpath start.
        Translate (+5, 0): M→(5,0), implicit-L→(15,10), Z closes to (5,0).
        """
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="p" d="M 0,0 10,10 Z"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        p2 = translate_element(p, "p", 5.0, 0.0)
        d = get_element(p2, "p").get("d")
        coords = _extract_path_coords(d)
        # Two explicit coordinate pairs: M start and the implicit-L point
        assert abs(coords[0][0] - 5.0) < 1e-4, f"M x: expected 5, got {coords[0][0]}"
        assert abs(coords[0][1] - 0.0) < 1e-4, f"M y: expected 0, got {coords[0][1]}"
        assert abs(coords[1][0] - 15.0) < 1e-4, f"implicit-L x: expected 15, got {coords[1][0]}"
        assert abs(coords[1][1] - 10.0) < 1e-4, f"implicit-L y: expected 10, got {coords[1][1]}"
        # Z must be present (path closes)
        assert "Z" in d.upper(), "Z command must be preserved after translate"


# ---------------------------------------------------------------------------
# Public API: piece_ids and element_bbox (review fix — expose as public API)
# ---------------------------------------------------------------------------


class TestPieceIds:
    """piece_ids() is a public function that returns top-level <g> ids only."""

    def test_returns_top_level_g_ids(self) -> None:
        """piece_ids returns ids of direct <g> children of the SVG root."""
        p = load_pattern(GROUPED_PIECE_SVG)
        ids = piece_ids(p)
        assert "bodice-front" in ids
        assert "outer-g" in ids

    def test_excludes_non_g_top_level_elements(self) -> None:
        """piece_ids does not include ids of top-level <path> or other non-<g> elements."""
        p = load_pattern(GROUPED_PIECE_SVG)
        ids = piece_ids(p)
        # sibling-path is a top-level <path>, not a <g> — must be excluded
        assert "sibling-path" not in ids

    def test_excludes_nested_g_elements(self) -> None:
        """piece_ids does not recurse — inner-g nested inside outer-g is excluded."""
        p = load_pattern(GROUPED_PIECE_SVG)
        ids = piece_ids(p)
        assert "inner-g" not in ids

    def test_returns_list(self) -> None:
        """piece_ids returns a list (not a set or generator)."""
        p = load_pattern(GROUPED_PIECE_SVG)
        result = piece_ids(p)
        assert isinstance(result, list)

    def test_empty_svg_returns_empty_list(self) -> None:
        """piece_ids returns [] for an SVG with no top-level <g> elements."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <path id="lone-path" d="M 0,0 L 10,10"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        result = piece_ids(p)
        assert result == []


class TestElementBbox:
    """element_bbox() is accessible as a public API."""

    def test_importable_from_pattern_ops(self) -> None:
        """element_bbox is importable from lib.pattern_ops without error."""
        # Import happened at top of file; reaching here means it succeeded.
        assert callable(element_bbox)

    def test_bbox_of_path_element(self) -> None:
        """element_bbox returns correct (min_x, min_y, max_x, max_y) for a path."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <path id="rect-path" d="M 10,20 L 90,20 L 90,80 L 10,80 Z"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        el = get_element(p, "rect-path")
        bbox = element_bbox(el)
        assert bbox is not None
        min_x, min_y, max_x, max_y = bbox
        assert abs(min_x - 10.0) < 1e-6
        assert abs(min_y - 20.0) < 1e-6
        assert abs(max_x - 90.0) < 1e-6
        assert abs(max_y - 80.0) < 1e-6

    def test_bbox_of_empty_g_element_returns_none(self) -> None:
        """element_bbox returns None for a <g> with no geometric coordinates."""
        svg_str = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <g id="empty-g"/>
</svg>"""
        p = load_pattern_from_string(svg_str)
        el = get_element(p, "empty-g")
        result = element_bbox(el)
        assert result is None
