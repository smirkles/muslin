"""Tests for backend/lib/cascade/fba.py — FBA cascade.

Each test corresponds to an acceptance criterion in docs/specs/15-fba-cascade.md.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from lxml import etree

BODICE_SVG = Path(__file__).parent.parent / "lib" / "patterns" / "bodice-v1" / "bodice-v1.svg"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_pattern():
    from lib.pattern_ops import load_pattern

    return load_pattern(BODICE_SVG)


def _element_exists(svg_str: str, element_id: str) -> bool:
    """Return True if an element with the given id is found in the SVG string."""
    root = etree.fromstring(svg_str.encode())
    for elem in root.iter():
        if elem.get("id") == element_id:
            return True
    return False


def _get_element(svg_str: str, element_id: str) -> etree._Element:
    """Return the lxml element with the given id, or raise AssertionError."""
    root = etree.fromstring(svg_str.encode())
    for elem in root.iter():
        if elem.get("id") == element_id:
            return elem
    raise AssertionError(f"Element '{element_id}' not found in SVG")


def _polygon_centroid_x(svg_str: str, element_id: str) -> float:
    """Return the centroid x of a polygon element."""
    el = _get_element(svg_str, element_id)
    tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
    assert tag == "polygon", f"Expected polygon, got {tag}"
    points_str = el.get("points", "")
    pairs = [p.split(",") for p in points_str.strip().split()]
    xs = [float(p[0]) for p in pairs if len(p) == 2]
    return sum(xs) / len(xs)


def _polygon_all_x(svg_str: str, element_id: str) -> list[float]:
    """Return all x-coordinates of a polygon element."""
    el = _get_element(svg_str, element_id)
    tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
    assert tag == "polygon", f"Expected polygon, got {tag}"
    points_str = el.get("points", "")
    pairs = [p.split(",") for p in points_str.strip().split()]
    return [float(p[0]) for p in pairs if len(p) == 2]


# ---------------------------------------------------------------------------
# Unit tests for apply_fba
# ---------------------------------------------------------------------------


class TestApplyFba:
    """Unit tests for lib.cascade.fba.apply_fba."""

    def test_returns_cascade_result_with_4_steps(self) -> None:
        """apply_fba returns CascadeResult with exactly 4 steps."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        assert len(result.cascade_script.steps) == 4

    def test_each_step_has_non_empty_narration(self) -> None:
        """Each step has a non-empty narration string."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        for step in result.cascade_script.steps:
            assert step.narration.strip() != "", f"Step {step.step_number} narration is empty"

    def test_each_step_has_valid_svg(self) -> None:
        """Each step has a valid SVG string parseable as XML."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        for step in result.cascade_script.steps:
            assert "<svg" in step.svg, f"Step {step.step_number} SVG missing <svg tag"
            etree.fromstring(step.svg.encode())  # Should not raise

    def test_each_step_has_step_number(self) -> None:
        """Each step has the correct step_number (1-indexed)."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        for i, step in enumerate(result.cascade_script.steps, start=1):
            assert step.step_number == i

    def test_step1_svg_parses_and_contains_front_panels(self) -> None:
        """Step 1 SVG is valid XML and contains front-cf-panel and front-side-panel."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        step1_svg = result.cascade_script.steps[0].svg

        # Must be parseable as XML
        etree.fromstring(step1_svg.encode())

        assert _element_exists(step1_svg, "front-cf-panel"), "front-cf-panel missing from step 1"
        assert _element_exists(
            step1_svg, "front-side-panel"
        ), "front-side-panel missing from step 1"

    def test_step2_svg_contains_slash_line(self) -> None:
        """Step 2 SVG contains a <line id='fba-slash-1'> element."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        step2_svg = result.cascade_script.steps[1].svg

        assert _element_exists(
            step2_svg, "fba-slash-1"
        ), "fba-slash-1 line element missing from step 2"

        el = _get_element(step2_svg, "fba-slash-1")
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        assert tag == "line", f"fba-slash-1 is a {tag}, expected line"

    def test_step3_front_side_panel_centroid_x_shifted_right(self) -> None:
        """Step 3: front-side-panel centroid x is shifted right by fba_px (±1px)."""
        from lib.cascade.fba import apply_fba

        fba_amount_cm = 2.5
        fba_px = fba_amount_cm * 10 * 0.5  # = 12.5

        pattern = _load_pattern()
        result = apply_fba(pattern, fba_amount_cm)

        cx2 = _polygon_centroid_x(result.cascade_script.steps[1].svg, "front-side-panel")
        cx3 = _polygon_centroid_x(result.cascade_script.steps[2].svg, "front-side-panel")

        actual_delta = cx3 - cx2
        assert actual_delta == pytest.approx(
            fba_px, abs=1
        ), f"front-side-panel centroid x delta {actual_delta:.2f} != expected {fba_px:.2f}"

    def test_step4_svg_contains_bust_dart_polygon(self) -> None:
        """Step 4 SVG contains a <polygon id='front-bust-dart'>."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        step4_svg = result.cascade_script.steps[3].svg

        assert _element_exists(
            step4_svg, "front-bust-dart"
        ), "front-bust-dart polygon missing from step 4"

        el = _get_element(step4_svg, "front-bust-dart")
        tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
        assert tag == "polygon", f"front-bust-dart is a {tag}, expected polygon"

    def test_front_cf_panel_unchanged_between_step1_and_step4(self) -> None:
        """front-cf-panel x-coordinates are unchanged between steps 1 and 4."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)

        xs1 = _polygon_all_x(result.cascade_script.steps[0].svg, "front-cf-panel")
        xs4 = _polygon_all_x(result.cascade_script.steps[3].svg, "front-cf-panel")

        assert xs1 == pytest.approx(
            xs4, abs=0.01
        ), "front-cf-panel x-coordinates changed during FBA"

    def test_back_piece_upper_unchanged_between_step1_and_step4(self) -> None:
        """back-piece-upper x-coordinates are unchanged between steps 1 and 4."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)

        xs1 = _polygon_all_x(result.cascade_script.steps[0].svg, "back-piece-upper")
        xs4 = _polygon_all_x(result.cascade_script.steps[3].svg, "back-piece-upper")

        assert xs1 == pytest.approx(
            xs4, abs=0.01
        ), "back-piece-upper x-coordinates changed during FBA (should only affect front)"

    def test_back_piece_lower_unchanged_between_step1_and_step4(self) -> None:
        """back-piece-lower x-coordinates are unchanged between steps 1 and 4."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)

        xs1 = _polygon_all_x(result.cascade_script.steps[0].svg, "back-piece-lower")
        xs4 = _polygon_all_x(result.cascade_script.steps[3].svg, "back-piece-lower")

        assert xs1 == pytest.approx(
            xs4, abs=0.01
        ), "back-piece-lower x-coordinates changed during FBA (should only affect front)"

    def test_input_pattern_not_mutated(self) -> None:
        """apply_fba does not mutate the input pattern."""
        from lib.cascade.fba import apply_fba
        from lib.pattern_ops import render_pattern

        pattern = _load_pattern()
        svg_before = render_pattern(pattern)
        apply_fba(pattern, 2.5)
        svg_after = render_pattern(pattern)
        assert svg_before == svg_after

    def test_adjusted_pattern_is_new_pattern_object(self) -> None:
        """adjusted_pattern is a new Pattern object, not the input."""
        from lib.cascade.fba import apply_fba
        from lib.pattern_ops import Pattern

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        assert isinstance(result.adjusted_pattern, Pattern)
        assert result.adjusted_pattern is not pattern

    def test_amount_too_small_raises_value_error(self) -> None:
        """amount_cm=0.4 raises ValueError with message containing '0.5'."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        with pytest.raises(ValueError, match="0.5"):
            apply_fba(pattern, 0.4)

    def test_amount_too_large_raises_value_error(self) -> None:
        """amount_cm=6.1 raises ValueError with message containing '6.0'."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        with pytest.raises(ValueError, match="6.0"):
            apply_fba(pattern, 6.1)

    def test_cascade_script_has_correct_adjustment_type(self) -> None:
        """cascade_script.adjustment_type == 'fba'."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        assert result.cascade_script.adjustment_type == "fba"

    def test_cascade_script_has_correct_amount_cm(self) -> None:
        """cascade_script.amount_cm matches input."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        assert result.cascade_script.amount_cm == pytest.approx(2.5)

    def test_cascade_script_has_correct_pattern_id(self) -> None:
        """cascade_script.pattern_id matches input."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5, pattern_id="bodice-v1")
        assert result.cascade_script.pattern_id == "bodice-v1"

    def test_step3_narration_contains_amount_cm(self) -> None:
        """Step 3 narration contains the fba_amount_cm value."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 2.5)
        step3 = result.cascade_script.steps[2]
        assert "2.5" in step3.narration, "fba_amount_cm not found in step 3 narration"

    def test_dart_geometry_tip_is_at_spread_edge(self) -> None:
        """Step 4 front-bust-dart tip x-coordinate is approximately 115 + fba_px."""
        from lib.cascade.fba import apply_fba

        fba_amount_cm = 2.5
        fba_px = fba_amount_cm * 10 * 0.5  # 12.5
        bust_column_x = 115
        expected_tip_x = bust_column_x + fba_px  # 127.5

        pattern = _load_pattern()
        result = apply_fba(pattern, fba_amount_cm)
        step4_svg = result.cascade_script.steps[3].svg

        el = _get_element(step4_svg, "front-bust-dart")
        points_str = el.get("points", "")
        pairs = [p.split(",") for p in points_str.strip().split()]
        xs = [float(p[0]) for p in pairs if len(p) == 2]

        # The tip (first point) should be at expected_tip_x
        assert xs[0] == pytest.approx(
            expected_tip_x, abs=1
        ), f"Dart tip x {xs[0]:.2f} not near expected {expected_tip_x:.2f}"

    def test_boundary_amount_min_is_valid(self) -> None:
        """amount_cm=0.5 (boundary) does not raise."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 0.5)
        assert len(result.cascade_script.steps) == 4

    def test_boundary_amount_max_is_valid(self) -> None:
        """amount_cm=6.0 (boundary) does not raise."""
        from lib.cascade.fba import apply_fba

        pattern = _load_pattern()
        result = apply_fba(pattern, 6.0)
        assert len(result.cascade_script.steps) == 4


# ---------------------------------------------------------------------------
# Integration tests against POST /cascades/apply-adjustment
# ---------------------------------------------------------------------------


class TestFbaRoute:
    """Integration tests for the /cascades/apply-adjustment route with FBA."""

    def _client(self):
        from fastapi.testclient import TestClient

        from main import app

        return TestClient(app)

    def test_valid_fba_returns_200(self) -> None:
        """Valid FBA request returns HTTP 200."""
        response = self._client().post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "fba", "amount_cm": 2.5},
        )
        assert response.status_code == 200

    def test_valid_fba_returns_4_steps(self) -> None:
        """Valid FBA response has exactly 4 steps."""
        response = self._client().post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "fba", "amount_cm": 2.5},
        )
        body = response.json()
        assert len(body["steps"]) == 4

    def test_steps_have_required_fields(self) -> None:
        """Each step has step_number, narration, and svg fields."""
        response = self._client().post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "fba", "amount_cm": 2.5},
        )
        for step in response.json()["steps"]:
            assert "step_number" in step
            assert "narration" in step
            assert "svg" in step
            assert len(step["narration"]) > 0
            assert "<svg" in step["svg"]

    def test_amount_too_small_returns_422(self) -> None:
        """amount_cm=0.3 returns HTTP 422."""
        response = self._client().post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "fba", "amount_cm": 0.3},
        )
        assert response.status_code == 422

    def test_nonexistent_pattern_id_returns_404(self) -> None:
        """Unknown pattern_id returns HTTP 404."""
        response = self._client().post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "nonexistent", "adjustment_type": "fba", "amount_cm": 2.5},
        )
        assert response.status_code == 404

    def test_unsupported_adjustment_type_returns_400(self) -> None:
        """Unsupported adjustment_type returns HTTP 400.

        Note: The spec says 422, but the existing route returns 400 for unknown
        adjustment types. We keep 400 to avoid breaking existing swayback tests.
        See implementation notes in spec 15.
        """
        response = self._client().post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "unsupported", "amount_cm": 2.5},
        )
        assert response.status_code == 400

    def test_response_adjustment_type_is_fba(self) -> None:
        """Response adjustment_type is 'fba'."""
        response = self._client().post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "fba", "amount_cm": 2.5},
        )
        assert response.json()["adjustment_type"] == "fba"
