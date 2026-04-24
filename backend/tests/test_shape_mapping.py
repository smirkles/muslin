"""Tests for lib/body_model/shape_mapping.py — measurements_to_betas()."""

import pytest

from lib.measurements import MeasurementsResponse
from lib.body_model.shape_mapping import measurements_to_betas

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REF_MEASUREMENTS = MeasurementsResponse(
    measurement_id="00000000-0000-0000-0000-000000000000",
    bust_cm=92.0,
    waist_cm=76.0,
    hip_cm=100.0,
    height_cm=168.0,
    back_length_cm=39.5,
    high_bust_cm=85.0,
    apex_to_apex_cm=18.0,
    size_label="12",
)


def _make_measurements(**overrides: float) -> MeasurementsResponse:
    """Return REF_MEASUREMENTS with specific fields overridden."""
    data = REF_MEASUREMENTS.model_dump()
    data.update(overrides)
    return MeasurementsResponse(**data)


# ---------------------------------------------------------------------------
# AC: Reference measurements → all zeros
# ---------------------------------------------------------------------------


class TestReferenceInputYieldsAllZeros:
    def test_reference_measurements_returns_all_zeros(self) -> None:
        """Reference measurements (bust=92, waist=76, hip=100, height=168) → [0.0]*10."""
        betas = measurements_to_betas(REF_MEASUREMENTS)
        assert all(b == 0.0 for b in betas), f"Expected all zeros, got {betas}"

    def test_returns_list_of_length_10(self) -> None:
        """Returned beta vector must always be length 10."""
        betas = measurements_to_betas(REF_MEASUREMENTS)
        assert len(betas) == 10


# ---------------------------------------------------------------------------
# AC: β[0] scaling for bust
# ---------------------------------------------------------------------------


class TestBustScaling:
    def test_bust_plus_20_gives_beta0_approx_1(self) -> None:
        """bust_cm = 112 (ref+20) → β[0] ≈ 1.0 ±0.01."""
        m = _make_measurements(bust_cm=112.0)
        betas = measurements_to_betas(m)
        assert abs(betas[0] - 1.0) <= 0.01, f"Expected β[0]≈1.0 got {betas[0]}"

    def test_bust_at_ref_gives_beta0_zero(self) -> None:
        """bust_cm = 92 → β[0] = 0.0."""
        betas = measurements_to_betas(REF_MEASUREMENTS)
        assert betas[0] == 0.0

    def test_bust_minus_20_gives_beta0_approx_minus1(self) -> None:
        """bust_cm = 72 (ref-20) → β[0] ≈ -1.0 ±0.01."""
        m = _make_measurements(bust_cm=72.0)
        betas = measurements_to_betas(m)
        assert abs(betas[0] - (-1.0)) <= 0.01, f"Expected β[0]≈-1.0 got {betas[0]}"


# ---------------------------------------------------------------------------
# AC: Clamping
# ---------------------------------------------------------------------------


class TestClamping:
    def test_extreme_high_bust_clamped_to_plus_3(self) -> None:
        """bust_cm = 250 → β[0] == 3.0 (clamped at +3)."""
        m = _make_measurements(bust_cm=250.0)
        betas = measurements_to_betas(m)
        assert betas[0] == 3.0, f"Expected β[0]==3.0 (clamped), got {betas[0]}"

    def test_extreme_low_bust_clamped_to_minus_3(self) -> None:
        """bust_cm = 20 → β[0] == -3.0 (clamped at -3)."""
        m = _make_measurements(bust_cm=20.0)
        betas = measurements_to_betas(m)
        assert betas[0] == -3.0, f"Expected β[0]==-3.0 (clamped), got {betas[0]}"

    def test_clamping_applies_per_component(self) -> None:
        """Extreme values for waist should also clamp independently."""
        m = _make_measurements(waist_cm=200.0)  # very high waist
        betas = measurements_to_betas(m)
        assert betas[1] == 3.0, f"Expected β[1]==3.0 (clamped), got {betas[1]}"

    def test_clamp_is_exactly_at_3(self) -> None:
        """Value that produces exactly 3.0 before clamping stays 3.0."""
        # bust_cm = 92 + 60 = 152 → (152-92)/20 = 3.0, not clamped but at boundary
        m = _make_measurements(bust_cm=152.0)
        betas = measurements_to_betas(m)
        assert betas[0] == 3.0


# ---------------------------------------------------------------------------
# AC: Length 10 regardless of inputs
# ---------------------------------------------------------------------------


class TestReturnLength:
    def test_length_10_with_extreme_values(self) -> None:
        """Even with extreme measurements, the beta vector is length 10."""
        m = _make_measurements(bust_cm=250.0, waist_cm=200.0, hip_cm=200.0, height_cm=220.0)
        betas = measurements_to_betas(m)
        assert len(betas) == 10

    def test_beta_4_through_9_are_zero(self) -> None:
        """β[4..9] must be 0.0 (these components are not used)."""
        betas = measurements_to_betas(REF_MEASUREMENTS)
        for i in range(4, 10):
            assert betas[i] == 0.0, f"Expected β[{i}]==0.0, got {betas[i]}"

    def test_beta_4_through_9_are_zero_with_non_ref_values(self) -> None:
        """β[4..9] must be 0.0 even for non-reference measurements."""
        m = _make_measurements(bust_cm=100.0, height_cm=175.0)
        betas = measurements_to_betas(m)
        for i in range(4, 10):
            assert betas[i] == 0.0, f"Expected β[{i}]==0.0, got {betas[i]}"


# ---------------------------------------------------------------------------
# AC: β[1], β[2], β[3] scaling
# ---------------------------------------------------------------------------


class TestOtherBetaScaling:
    def test_waist_plus_20_gives_beta1_approx_1(self) -> None:
        """waist_cm = 96 (ref+20) → β[1] ≈ 1.0 ±0.01."""
        m = _make_measurements(waist_cm=96.0)
        betas = measurements_to_betas(m)
        assert abs(betas[1] - 1.0) <= 0.01, f"Expected β[1]≈1.0 got {betas[1]}"

    def test_hip_plus_20_gives_beta2_approx_1(self) -> None:
        """hip_cm = 120 (ref+20) → β[2] ≈ 1.0 ±0.01."""
        m = _make_measurements(hip_cm=120.0)
        betas = measurements_to_betas(m)
        assert abs(betas[2] - 1.0) <= 0.01, f"Expected β[2]≈1.0 got {betas[2]}"

    def test_height_plus_10_gives_beta3_approx_1(self) -> None:
        """height_cm = 178 (ref+10) → β[3] ≈ 1.0 ±0.01."""
        m = _make_measurements(height_cm=178.0)
        betas = measurements_to_betas(m)
        assert abs(betas[3] - 1.0) <= 0.01, f"Expected β[3]≈1.0 got {betas[3]}"


# ---------------------------------------------------------------------------
# AC: No fastapi imports in lib/body_model/
# ---------------------------------------------------------------------------


class TestImportHygiene:
    def test_shape_mapping_has_no_fastapi_import(self) -> None:
        """lib/body_model/shape_mapping must not import fastapi."""
        import importlib.util
        import os

        spec_file = os.path.join(
            os.path.dirname(__file__), "..", "lib", "body_model", "shape_mapping.py"
        )
        source = open(spec_file).read()
        assert "fastapi" not in source, "shape_mapping.py must not import fastapi"
