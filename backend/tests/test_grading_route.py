"""Route tests for POST /patterns/{pattern_id}/grade (spec 10).

Uses TestClient to test the full request/response cycle.

Requires:
- A registered pattern with base_bust_cm etc. in its meta.json (bodice-v1)
- A valid measurement_id from POST /measurements
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_MEASUREMENTS = {
    "bust_cm": 96.0,
    "high_bust_cm": 85.0,
    "apex_to_apex_cm": 18.0,
    "waist_cm": 78.0,
    "hip_cm": 104.0,
    "height_cm": 168.0,
    "back_length_cm": 41.0,
}


def _post_measurements() -> str:
    """Create a measurements record and return its measurement_id."""
    resp = client.post("/measurements", json=VALID_MEASUREMENTS)
    assert resp.status_code == 200, f"Measurements POST failed: {resp.text}"
    return resp.json()["measurement_id"]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestGradePatternHappyPath:
    """Tests for 200 OK on POST /patterns/{pattern_id}/grade."""

    def test_returns_200_for_known_pattern_and_measurement(self) -> None:
        """AC: valid pattern_id and measurement_id → 200 OK."""
        mid = _post_measurements()
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid})
        assert resp.status_code == 200, resp.text

    def test_response_has_graded_pattern_id(self) -> None:
        """AC: response includes graded_pattern_id field."""
        mid = _post_measurements()
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid})
        assert resp.status_code == 200
        assert "graded_pattern_id" in resp.json()

    def test_graded_pattern_id_is_uuid_format(self) -> None:
        """AC: graded_pattern_id is a UUID string (36 chars with hyphens)."""
        mid = _post_measurements()
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid})
        assert resp.status_code == 200
        gpid = resp.json()["graded_pattern_id"]
        assert isinstance(gpid, str)
        # Validate as UUID
        try:
            uuid.UUID(gpid)
        except ValueError:
            pytest.fail(f"graded_pattern_id is not a valid UUID: {gpid!r}")

    def test_response_has_svg_field(self) -> None:
        """AC: response includes svg field."""
        mid = _post_measurements()
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid})
        assert resp.status_code == 200
        assert "svg" in resp.json()

    def test_svg_is_non_empty_and_contains_svg_tag(self) -> None:
        """AC: svg field is non-empty and contains '<svg'."""
        mid = _post_measurements()
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid})
        assert resp.status_code == 200
        svg = resp.json()["svg"]
        assert isinstance(svg, str)
        assert len(svg) > 0
        assert "<svg" in svg

    def test_response_has_adjustments_cm_field(self) -> None:
        """AC: response includes adjustments_cm field."""
        mid = _post_measurements()
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid})
        assert resp.status_code == 200
        assert "adjustments_cm" in resp.json()

    def test_adjustments_cm_has_exactly_required_keys(self) -> None:
        """AC: adjustments_cm has exactly bust, waist, hip, back_length keys."""
        mid = _post_measurements()
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid})
        assert resp.status_code == 200
        adj = resp.json()["adjustments_cm"]
        assert set(adj.keys()) == {"bust", "waist", "hip", "back_length"}

    def test_response_has_pattern_id_and_measurement_id(self) -> None:
        """AC: response echoes pattern_id and measurement_id."""
        mid = _post_measurements()
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid})
        assert resp.status_code == 200
        body = resp.json()
        assert body["pattern_id"] == "bodice-v1"
        assert body["measurement_id"] == mid

    def test_two_calls_produce_distinct_graded_pattern_ids(self) -> None:
        """AC: two grade calls produce distinct graded_pattern_id values."""
        mid1 = _post_measurements()
        mid2 = _post_measurements()
        resp1 = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid1})
        resp2 = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid2})
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["graded_pattern_id"] != resp2.json()["graded_pattern_id"]

    def test_adjustments_cm_values_are_floats(self) -> None:
        """AC: each adjustments_cm value is a float (or int == float)."""
        mid = _post_measurements()
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": mid})
        assert resp.status_code == 200
        adj = resp.json()["adjustments_cm"]
        for v in adj.values():
            assert isinstance(v, (int, float))


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestGradePatternErrors:
    """Tests for error responses from POST /patterns/{pattern_id}/grade."""

    def test_unknown_pattern_id_returns_404(self) -> None:
        """AC: unknown pattern_id → 404."""
        mid = _post_measurements()
        resp = client.post("/patterns/does-not-exist/grade", json={"measurement_id": mid})
        assert resp.status_code == 404

    def test_404_for_unknown_pattern_detail_mentions_id(self) -> None:
        """AC: 404 detail mentions the unknown pattern id."""
        mid = _post_measurements()
        resp = client.post("/patterns/does-not-exist/grade", json={"measurement_id": mid})
        assert resp.status_code == 404
        assert "does-not-exist" in resp.json()["detail"]

    def test_unknown_measurement_id_returns_404(self) -> None:
        """AC: unknown measurement_id → 404."""
        fake_mid = "00000000-0000-0000-0000-000000000000"
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": fake_mid})
        assert resp.status_code == 404

    def test_404_for_unknown_measurement_mentions_measurements(self) -> None:
        """AC: 404 detail mentions 'Measurements' (or the id)."""
        fake_mid = "00000000-0000-0000-0000-000000000000"
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": fake_mid})
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert fake_mid in detail or "Measurements" in detail or "measurements" in detail

    def test_missing_body_returns_422(self) -> None:
        """AC: missing body → 422."""
        resp = client.post("/patterns/bodice-v1/grade")
        assert resp.status_code == 422

    def test_missing_measurement_id_field_returns_422(self) -> None:
        """AC: body missing measurement_id field → 422."""
        resp = client.post("/patterns/bodice-v1/grade", json={})
        assert resp.status_code == 422

    def test_null_measurement_id_returns_422(self) -> None:
        """AC: null measurement_id → 422 (Pydantic will reject None for str)."""
        resp = client.post("/patterns/bodice-v1/grade", json={"measurement_id": None})
        assert resp.status_code == 422
