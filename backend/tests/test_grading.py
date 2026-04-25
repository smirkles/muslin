"""Unit tests for lib/grading.py — grade_pattern, store_graded_pattern, get_graded_pattern.

Covers all acceptance criteria from spec 10-pattern-grading.

Fixture: tests/fixtures/patterns/two_piece.svg
  bodice-front piece: polygon points 10,10 110,10 110,210 10,210
    → width  = 100px (x range 10..110)
    → height = 200px (y range 10..210)
  skirt-front piece:  polygon points 10,220 110,220 110,420 10,420
    → width  = 100px (x range 10..110)
    → height = 200px (y range 220..420)
"""

from __future__ import annotations

import importlib
import re
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

# Path to the two-piece fixture
FIXTURE_SVG = Path(__file__).parent / "fixtures" / "patterns" / "two_piece.svg"

# ---------------------------------------------------------------------------
# Helper: parse polygon x/y lists from SVG string
# ---------------------------------------------------------------------------


def _parse_points(svg: str, element_id: str) -> list[tuple[float, float]]:
    """Extract polygon points for an element by id from an SVG string.

    Returns list of (x, y) tuples.
    """
    # Find the points attribute for the element
    pattern = rf'id="{element_id}"[^>]*points="([^"]+)"'
    m = re.search(pattern, svg)
    if not m:
        # Also try reversed attribute order
        pattern2 = rf'points="([^"]+)"[^>]*id="{element_id}"'
        m = re.search(pattern2, svg)
    assert m is not None, f"Could not find points for element '{element_id}' in SVG"
    raw = m.group(1)
    nums = [float(t) for t in re.split(r"[,\s]+", raw.strip()) if t]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


def _bbox_from_points(pts: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) from a list of (x, y) tuples."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_width(pts: list[tuple[float, float]]) -> float:
    bx = _bbox_from_points(pts)
    return bx[2] - bx[0]


def _bbox_height(pts: list[tuple[float, float]]) -> float:
    bx = _bbox_from_points(pts)
    return bx[3] - bx[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_meas() -> dict:
    """Base measurements matching the spec example."""
    return {
        "bust_cm": 92.0,
        "waist_cm": 74.0,
        "hip_cm": 100.0,
        "back_length_cm": 40.0,
    }


@pytest.fixture
def user_meas_larger() -> dict:
    """User measurements larger than base — spec example."""
    return {
        "bust_cm": 96.0,
        "waist_cm": 78.0,
        "hip_cm": 104.0,
        "back_length_cm": 41.0,
    }


@pytest.fixture
def user_meas_identical(base_meas: dict) -> dict:
    """User measurements identical to base."""
    return dict(base_meas)


@pytest.fixture
def user_meas_smaller() -> dict:
    """User measurements smaller than base — tests negative adjustments."""
    return {
        "bust_cm": 88.0,
        "waist_cm": 70.0,
        "hip_cm": 96.0,
        "back_length_cm": 39.0,
    }


@pytest.fixture
def pattern():
    """Load the two-piece test fixture as a Pattern object."""
    from lib.pattern_ops import load_pattern

    return load_pattern(FIXTURE_SVG)


@pytest.fixture
def base_measurements_obj(base_meas: dict):
    """Return BaseMeasurements dataclass from grading module."""
    from lib.grading import BaseMeasurements

    return BaseMeasurements(**base_meas)


@pytest.fixture
def user_measurements_larger_obj(user_meas_larger: dict):
    """Return user Measurements pydantic model (larger)."""
    from lib.measurements import Measurements

    return Measurements(
        bust_cm=user_meas_larger["bust_cm"],
        high_bust_cm=80.0,  # required field, not used by grading
        apex_to_apex_cm=18.0,  # required field, not used by grading
        waist_cm=user_meas_larger["waist_cm"],
        hip_cm=user_meas_larger["hip_cm"],
        height_cm=168.0,  # required field, not used by grading
        back_length_cm=user_meas_larger["back_length_cm"],
    )


@pytest.fixture
def user_measurements_identical_obj(base_meas: dict):
    """Return user Measurements pydantic model (identical to base)."""
    from lib.measurements import Measurements

    return Measurements(
        bust_cm=base_meas["bust_cm"],
        high_bust_cm=80.0,
        apex_to_apex_cm=18.0,
        waist_cm=base_meas["waist_cm"],
        hip_cm=base_meas["hip_cm"],
        height_cm=168.0,
        back_length_cm=base_meas["back_length_cm"],
    )


@pytest.fixture
def user_measurements_smaller_obj(user_meas_smaller: dict):
    """Return user Measurements pydantic model (smaller)."""
    from lib.measurements import Measurements

    return Measurements(
        bust_cm=user_meas_smaller["bust_cm"],
        high_bust_cm=76.0,
        apex_to_apex_cm=17.0,
        waist_cm=user_meas_smaller["waist_cm"],
        hip_cm=user_meas_smaller["hip_cm"],
        height_cm=165.0,
        back_length_cm=user_meas_smaller["back_length_cm"],
    )


# ---------------------------------------------------------------------------
# Import-hygiene test — MUST run even before implementation exists
# ---------------------------------------------------------------------------


class TestImportHygiene:
    """lib/grading.py must not import from fastapi, starlette, or routes/."""

    def test_grading_has_no_fastapi_imports(self) -> None:
        """Verify grading.py source contains no 'import fastapi' or 'from fastapi'."""
        grading_path = Path(__file__).parent.parent / "lib" / "grading.py"
        assert grading_path.exists(), "lib/grading.py does not exist yet"
        source = grading_path.read_text(encoding="utf-8")
        assert "fastapi" not in source, "lib/grading.py must not import fastapi"
        assert "starlette" not in source, "lib/grading.py must not import starlette"

    def test_grading_module_imports_without_fastapi(self) -> None:
        """grading module can be imported without fastapi being required."""
        # Ensure fresh import
        if "lib.grading" in sys.modules:
            del sys.modules["lib.grading"]
        mod = importlib.import_module("lib.grading")
        # Just checking it loads — if it tried to import fastapi and fastapi
        # wasn't installed, it would raise ImportError.
        assert hasattr(mod, "grade_pattern")
        assert hasattr(mod, "store_graded_pattern")
        assert hasattr(mod, "get_graded_pattern")


# ---------------------------------------------------------------------------
# AC: adjustments_cm values with spec example measurements
# ---------------------------------------------------------------------------


class TestAdjustmentsCm:
    """Test that adjustments_cm is computed correctly."""

    def test_spec_example_adjustments(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_larger_obj,
    ) -> None:
        """AC: bust=92→96, waist=74→78, hip=100→104, back_length=40→41 → all +4 or +1."""
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-1",
        )
        assert g.adjustments_cm == {
            "bust": 4.0,
            "waist": 4.0,
            "hip": 4.0,
            "back_length": 1.0,
        }

    def test_adjustments_are_rounded_to_one_decimal(
        self,
        pattern,
        base_measurements_obj,
    ) -> None:
        """AC: adjustments are rounded to 1 decimal place."""
        from lib.grading import grade_pattern
        from lib.measurements import Measurements

        # 96.7 - 92 = 4.7  (already clean to 1 dp)
        # 74.33 - 74 = 0.3 (needs rounding from raw float)
        user = Measurements(
            bust_cm=96.7,
            high_bust_cm=80.0,
            apex_to_apex_cm=18.0,
            waist_cm=74.3,
            hip_cm=100.0,
            height_cm=168.0,
            back_length_cm=40.0,
        )
        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user,
            pattern_id="two-piece",
            measurement_id="test-id-2",
        )
        # Check rounding (1 decimal place)
        assert g.adjustments_cm["bust"] == round(96.7 - 92.0, 1)
        assert g.adjustments_cm["waist"] == round(74.3 - 74.0, 1)
        assert g.adjustments_cm["hip"] == 0.0
        assert g.adjustments_cm["back_length"] == 0.0

    def test_negative_adjustment_when_user_smaller_than_base(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_smaller_obj,
    ) -> None:
        """AC: user smaller than base → negative adjustments_cm."""
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_smaller_obj,
            pattern_id="two-piece",
            measurement_id="test-id-3",
        )
        assert g.adjustments_cm["bust"] < 0.0
        assert g.adjustments_cm["hip"] < 0.0
        assert g.adjustments_cm["back_length"] < 0.0

    def test_adjustments_keys_are_exactly_four(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_larger_obj,
    ) -> None:
        """AC: adjustments_cm has exactly bust, waist, hip, back_length keys."""
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-4",
        )
        assert set(g.adjustments_cm.keys()) == {"bust", "waist", "hip", "back_length"}


# ---------------------------------------------------------------------------
# AC: identity case — identical measurements → coordinates unchanged
# ---------------------------------------------------------------------------


class TestIdentityCase:
    """AC: identical base and user → adjustments 0.0 and coordinates unchanged."""

    def test_identity_adjustments_are_zero(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_identical_obj,
    ) -> None:
        """All adjustments_cm are 0.0 when user equals base."""
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_identical_obj,
            pattern_id="two-piece",
            measurement_id="test-id-5",
        )
        for v in g.adjustments_cm.values():
            assert v == 0.0

    def test_identity_bodice_width_unchanged(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_identical_obj,
    ) -> None:
        """AC: identical measurements → bodice bounding-box width within 1e-6 of original."""
        from lib.pattern_ops import render_pattern
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_identical_obj,
            pattern_id="two-piece",
            measurement_id="test-id-6",
        )
        original_pts = _parse_points(render_pattern(pattern), "bodice-front-rect")
        graded_pts = _parse_points(g.svg, "bodice-front-rect")

        orig_w = _bbox_width(original_pts)
        graded_w = _bbox_width(graded_pts)
        assert abs(graded_w - orig_w) < 1e-6

    def test_identity_skirt_height_unchanged(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_identical_obj,
    ) -> None:
        """AC: identical measurements → skirt bounding-box height within 1e-6 of original."""
        from lib.pattern_ops import render_pattern
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_identical_obj,
            pattern_id="two-piece",
            measurement_id="test-id-7",
        )
        original_pts = _parse_points(render_pattern(pattern), "skirt-front-rect")
        graded_pts = _parse_points(g.svg, "skirt-front-rect")

        orig_h = _bbox_height(original_pts)
        graded_h = _bbox_height(graded_pts)
        assert abs(graded_h - orig_h) < 1e-6


# ---------------------------------------------------------------------------
# AC: piece-level scaling — bodice scales by bust ratio
# ---------------------------------------------------------------------------


class TestBodiceScaling:
    """AC: bodice- pieces scale horizontally by user_bust / base_bust."""

    def test_bodice_width_scales_by_bust_ratio(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_larger_obj,
    ) -> None:
        """AC: bodice-front bounding-box width ratio equals user_bust/base_bust (±1e-6)."""
        from lib.pattern_ops import render_pattern
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-8",
        )
        original_pts = _parse_points(render_pattern(pattern), "bodice-front-rect")
        graded_pts = _parse_points(g.svg, "bodice-front-rect")

        orig_w = _bbox_width(original_pts)
        graded_w = _bbox_width(graded_pts)
        expected_ratio = user_measurements_larger_obj.bust_cm / base_measurements_obj.bust_cm
        assert abs(graded_w / orig_w - expected_ratio) < 1e-6

    def test_bodice_negative_scaling_reduces_width(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_smaller_obj,
    ) -> None:
        """AC: user bust < base bust → bodice bounding-box width strictly smaller."""
        from lib.pattern_ops import render_pattern
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_smaller_obj,
            pattern_id="two-piece",
            measurement_id="test-id-9",
        )
        original_pts = _parse_points(render_pattern(pattern), "bodice-front-rect")
        graded_pts = _parse_points(g.svg, "bodice-front-rect")

        assert _bbox_width(graded_pts) < _bbox_width(original_pts)


# ---------------------------------------------------------------------------
# AC: piece-level scaling — skirt scales by hip ratio
# ---------------------------------------------------------------------------


class TestSkirtScaling:
    """AC: skirt- pieces scale horizontally by user_hip / base_hip."""

    def test_skirt_width_scales_by_hip_ratio(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_larger_obj,
    ) -> None:
        """AC: skirt-front bounding-box width ratio equals user_hip/base_hip (±1e-6)."""
        from lib.pattern_ops import render_pattern
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-10",
        )
        original_pts = _parse_points(render_pattern(pattern), "skirt-front-rect")
        graded_pts = _parse_points(g.svg, "skirt-front-rect")

        orig_w = _bbox_width(original_pts)
        graded_w = _bbox_width(graded_pts)
        expected_ratio = user_measurements_larger_obj.hip_cm / base_measurements_obj.hip_cm
        assert abs(graded_w / orig_w - expected_ratio) < 1e-6


# ---------------------------------------------------------------------------
# AC: vertical scaling — ALL pieces scale by back_length ratio
# ---------------------------------------------------------------------------


class TestVerticalScaling:
    """AC: all pieces scale vertically by user_back_length / base_back_length."""

    def test_bodice_height_scales_by_back_length_ratio(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_larger_obj,
    ) -> None:
        """AC: bodice-front bounding-box height ratio equals back_length ratio (±1e-6)."""
        from lib.pattern_ops import render_pattern
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-11",
        )
        original_pts = _parse_points(render_pattern(pattern), "bodice-front-rect")
        graded_pts = _parse_points(g.svg, "bodice-front-rect")

        orig_h = _bbox_height(original_pts)
        graded_h = _bbox_height(graded_pts)
        expected_ratio = user_measurements_larger_obj.back_length_cm / base_measurements_obj.back_length_cm
        assert abs(graded_h / orig_h - expected_ratio) < 1e-6

    def test_skirt_height_scales_by_back_length_ratio(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_larger_obj,
    ) -> None:
        """AC: skirt-front bounding-box height ratio equals back_length ratio (±1e-6)."""
        from lib.pattern_ops import render_pattern
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-12",
        )
        original_pts = _parse_points(render_pattern(pattern), "skirt-front-rect")
        graded_pts = _parse_points(g.svg, "skirt-front-rect")

        orig_h = _bbox_height(original_pts)
        graded_h = _bbox_height(graded_pts)
        expected_ratio = user_measurements_larger_obj.back_length_cm / base_measurements_obj.back_length_cm
        assert abs(graded_h / orig_h - expected_ratio) < 1e-6


# ---------------------------------------------------------------------------
# AC: input pattern is unchanged
# ---------------------------------------------------------------------------


class TestInputImmutability:
    """AC: grade_pattern returns a new object; input pattern is unchanged."""

    def test_original_pattern_svg_unchanged(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_larger_obj,
    ) -> None:
        """grade_pattern does not mutate the input Pattern object."""
        from lib.pattern_ops import render_pattern
        from lib.grading import grade_pattern

        svg_before = render_pattern(pattern)
        grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-13",
        )
        svg_after = render_pattern(pattern)
        assert svg_before == svg_after


# ---------------------------------------------------------------------------
# AC: session store round-trip
# ---------------------------------------------------------------------------


class TestSessionStore:
    """Tests for store_graded_pattern / get_graded_pattern."""

    def test_store_then_get_returns_equal_object(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_larger_obj,
    ) -> None:
        """AC: store then get returns an equal GradedPattern."""
        from lib.grading import grade_pattern, get_graded_pattern, store_graded_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-14",
        )
        store_graded_pattern(g)
        retrieved = get_graded_pattern(g.graded_pattern_id)
        assert retrieved == g

    def test_get_unknown_id_raises_key_error(self) -> None:
        """AC: get_graded_pattern raises KeyError for unknown id."""
        from lib.grading import get_graded_pattern

        with pytest.raises(KeyError):
            get_graded_pattern("00000000-0000-0000-0000-000000000000")

    def test_two_successive_calls_produce_distinct_ids(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_larger_obj,
    ) -> None:
        """AC: two grade_pattern calls produce distinct graded_pattern_id values."""
        from lib.grading import grade_pattern

        g1 = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-15",
        )
        g2 = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-16",
        )
        assert g1.graded_pattern_id != g2.graded_pattern_id

    def test_stored_graded_pattern_has_correct_fields(
        self,
        pattern,
        base_measurements_obj,
        user_measurements_larger_obj,
    ) -> None:
        """GradedPattern has all required fields with correct types."""
        from lib.grading import grade_pattern

        g = grade_pattern(
            pattern,
            base_measurements_obj,
            user_measurements_larger_obj,
            pattern_id="two-piece",
            measurement_id="test-id-17",
        )
        assert isinstance(g.graded_pattern_id, str)
        assert isinstance(g.pattern_id, str)
        assert isinstance(g.measurement_id, str)
        assert isinstance(g.svg, str)
        assert isinstance(g.adjustments_cm, dict)
        assert g.pattern_id == "two-piece"
        assert g.measurement_id == "test-id-17"
