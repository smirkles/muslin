"""Tests for backend/lib/cascade/swayback.py — swayback cascade."""

import ast
from pathlib import Path

import pytest
from lxml import etree

BODICE_SVG = Path(__file__).parent.parent / "lib" / "patterns" / "bodice-v1" / "bodice-v1.svg"
CASCADE_PKG = Path(__file__).parent.parent / "lib" / "cascade"


def _centroid_y(svg_str: str, element_id: str) -> float:
    """Parse SVG string and return the centroid y of the polygon with given id."""
    root = etree.fromstring(svg_str.encode())
    # Search with and without namespace
    el = root.find(f".//*[@id='{element_id}']")
    if el is None:
        # Try recursive search
        for elem in root.iter():
            if elem.get("id") == element_id:
                el = elem
                break
    assert el is not None, f"Element '{element_id}' not found in SVG"

    tag = el.tag.split("}")[-1] if "}" in el.tag else el.tag
    if tag == "polygon":
        points_str = el.get("points", "")
        pairs = [p.split(",") for p in points_str.strip().split()]
        ys = [float(p[1]) for p in pairs if len(p) == 2]
        return sum(ys) / len(ys)
    elif tag == "line":
        y1 = float(el.get("y1", 0))
        y2 = float(el.get("y2", 0))
        return (y1 + y2) / 2
    raise ValueError(f"Unsupported element type: {tag}")


def _element_exists(svg_str: str, element_id: str) -> bool:
    root = etree.fromstring(svg_str.encode())
    for elem in root.iter():
        if elem.get("id") == element_id:
            return True
    return False


def _get_element_attr(svg_str: str, element_id: str, attr: str) -> str:
    root = etree.fromstring(svg_str.encode())
    for elem in root.iter():
        if elem.get("id") == element_id:
            return elem.get(attr, "")
    raise KeyError(f"Element '{element_id}' not found")


class TestApplySwayback:
    def _load_pattern(self):
        from lib.pattern_ops import load_pattern

        return load_pattern(BODICE_SVG)

    def test_returns_cascade_result_with_5_steps(self) -> None:
        """apply_swayback returns CascadeResult with exactly 5 steps."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        result = apply_swayback(pattern, 1.5)
        assert len(result.cascade_script.steps) == 5

    def test_each_step_has_non_empty_narration(self) -> None:
        """Each step has a non-empty narration string."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        result = apply_swayback(pattern, 1.5)
        for step in result.cascade_script.steps:
            assert step.narration.strip() != "", f"Step {step.step_number} narration is empty"

    def test_each_step_has_valid_svg(self) -> None:
        """Each step has a valid SVG string parseable as XML."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        result = apply_swayback(pattern, 1.5)
        for step in result.cascade_script.steps:
            assert "<svg" in step.svg, f"Step {step.step_number} SVG missing <svg tag"
            etree.fromstring(step.svg.encode())  # Should not raise

    def test_narration_contains_amount_cm_substitution(self) -> None:
        """Step 3 narration has {amount_cm} substituted with actual value."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        result = apply_swayback(pattern, 1.5)
        step3 = result.cascade_script.steps[2]
        assert "1.5" in step3.narration, "amount_cm not substituted in step 3 narration"
        assert "{amount_cm}" not in step3.narration

    def test_step2_svg_contains_fold_line_at_waist_y(self) -> None:
        """Step 2 SVG contains swayback-fold-line with y=160."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        result = apply_swayback(pattern, 1.5)
        step2_svg = result.cascade_script.steps[1].svg
        assert _element_exists(step2_svg, "swayback-fold-line")
        y1 = _get_element_attr(step2_svg, "swayback-fold-line", "y1")
        y2 = _get_element_attr(step2_svg, "swayback-fold-line", "y2")
        assert float(y1) == pytest.approx(160, abs=1)
        assert float(y2) == pytest.approx(160, abs=1)

    def test_step3_back_lower_centroid_y_less_than_step2(self) -> None:
        """Step 3: back-piece-lower centroid y is less than in step 2 (piece moved up)."""
        from lib.cascade.constants import SCALE
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        amount_cm = 1.5
        result = apply_swayback(pattern, amount_cm)

        y2 = _centroid_y(result.cascade_script.steps[1].svg, "back-piece-lower")
        y3 = _centroid_y(result.cascade_script.steps[2].svg, "back-piece-lower")

        swayback_px = amount_cm * SCALE
        expected_delta = swayback_px / 2
        actual_delta = y2 - y3
        assert actual_delta == pytest.approx(
            expected_delta, abs=3
        ), f"centroid y delta {actual_delta:.2f} not near {expected_delta:.2f}"

    def test_front_elements_unchanged_between_step1_and_step5(self) -> None:
        """Front elements (front-cf-panel) are byte-identical in step 1 and step 5."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        result = apply_swayback(pattern, 1.5)

        step1 = result.cascade_script.steps[0].svg
        step5 = result.cascade_script.steps[4].svg

        def _get_element_xml(svg_str: str, element_id: str) -> str:
            root = etree.fromstring(svg_str.encode())
            for elem in root.iter():
                if elem.get("id") == element_id:
                    return etree.tostring(elem, encoding="unicode")
            return ""

        front_step1 = _get_element_xml(step1, "front-cf-panel")
        front_step5 = _get_element_xml(step5, "front-cf-panel")
        assert front_step1 == front_step5

    def test_input_pattern_not_mutated(self) -> None:
        """apply_swayback does not mutate the input pattern."""
        from lib.cascade.swayback import apply_swayback
        from lib.pattern_ops import render_pattern

        pattern = self._load_pattern()
        svg_before = render_pattern(pattern)
        apply_swayback(pattern, 1.5)
        svg_after = render_pattern(pattern)
        assert svg_before == svg_after

    def test_seam_adjustments_has_correct_keys(self) -> None:
        """cascade_script.seam_adjustments has exactly the expected keys."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        result = apply_swayback(pattern, 1.5)
        keys = set(result.cascade_script.seam_adjustments.keys())
        assert keys == {"cb_seam_delta_cm", "side_seam_delta_cm", "waist_seam_delta_cm"}

    def test_cb_seam_delta_equals_negative_amount(self) -> None:
        """cb_seam_delta_cm == -swayback_amount_cm."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        result = apply_swayback(pattern, 1.5)
        assert result.cascade_script.seam_adjustments["cb_seam_delta_cm"] == pytest.approx(
            -1.5, abs=0.01
        )

    def test_side_seam_delta_is_zero(self) -> None:
        """side_seam_delta_cm == 0.0."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        result = apply_swayback(pattern, 1.5)
        assert result.cascade_script.seam_adjustments["side_seam_delta_cm"] == pytest.approx(
            0.0, abs=0.01
        )

    def test_amount_too_small_raises_value_error(self) -> None:
        """amount_cm=0.4 raises ValueError mentioning '0.5'."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        with pytest.raises(ValueError, match="0.5"):
            apply_swayback(pattern, 0.4)

    def test_amount_too_large_raises_value_error(self) -> None:
        """amount_cm=2.6 raises ValueError mentioning '2.5'."""
        from lib.cascade.swayback import apply_swayback

        pattern = self._load_pattern()
        with pytest.raises(ValueError, match="2.5"):
            apply_swayback(pattern, 2.6)

    def test_cascade_result_has_adjusted_pattern(self) -> None:
        """CascadeResult.adjusted_pattern is a Pattern object."""
        from lib.cascade.swayback import apply_swayback
        from lib.pattern_ops import Pattern

        pattern = self._load_pattern()
        result = apply_swayback(pattern, 1.5)
        assert isinstance(result.adjusted_pattern, Pattern)


class TestImportHygiene:
    def test_cascade_lib_does_not_import_fastapi(self) -> None:
        """lib/cascade/ source files must not import FastAPI."""
        assert CASCADE_PKG.exists()
        forbidden = {"fastapi", "starlette"}

        for py_file in CASCADE_PKG.rglob("*.py"):
            source = py_file.read_text()
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for bad in forbidden:
                            assert (
                                bad not in alias.name
                            ), f"{py_file.name} imports forbidden module '{alias.name}'"
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for bad in forbidden:
                        assert (
                            bad not in module
                        ), f"{py_file.name} imports from forbidden module '{module}'"
