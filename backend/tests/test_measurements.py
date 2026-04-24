"""Tests for POST /measurements endpoint and lib/measurements.py."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from lib.measurements import Measurements, derive_size_label
from main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Unit tests: derive_size_label boundary checks
# ---------------------------------------------------------------------------


class TestDeriveSizeLabel:
    """Test size label derivation at every boundary from the spec table."""

    def test_below_83_returns_size_8(self) -> None:
        """Bust < 83 → size 8."""
        assert derive_size_label(60.0) == "8"
        assert derive_size_label(82.9) == "8"

    def test_exactly_82_returns_size_8(self) -> None:
        """Bust == 82 → size 8 (still below 83 boundary)."""
        assert derive_size_label(82.0) == "8"

    def test_exactly_83_returns_size_10(self) -> None:
        """Bust == 83 → size 10 (lower bound of 83–87 range)."""
        assert derive_size_label(83.0) == "10"

    def test_exactly_87_returns_size_10(self) -> None:
        """Bust == 87 → size 10 (upper bound of 83–87 range)."""
        assert derive_size_label(87.0) == "10"

    def test_exactly_88_returns_size_12(self) -> None:
        """Bust == 88 → size 12."""
        assert derive_size_label(88.0) == "12"

    def test_exactly_92_returns_size_12(self) -> None:
        """Bust == 92 → size 12 (upper bound of 88–92 range)."""
        assert derive_size_label(92.0) == "12"

    def test_exactly_93_returns_size_14(self) -> None:
        """Bust == 93 → size 14."""
        assert derive_size_label(93.0) == "14"

    def test_exactly_97_returns_size_14(self) -> None:
        """Bust == 97 → size 14 (upper bound of 93–97 range)."""
        assert derive_size_label(97.0) == "14"

    def test_exactly_98_returns_size_16(self) -> None:
        """Bust == 98 → size 16."""
        assert derive_size_label(98.0) == "16"

    def test_exactly_102_returns_size_16(self) -> None:
        """Bust == 102 → size 16 (upper bound of 98–102 range)."""
        assert derive_size_label(102.0) == "16"

    def test_exactly_103_returns_size_18(self) -> None:
        """Bust == 103 → size 18."""
        assert derive_size_label(103.0) == "18"

    def test_exactly_107_returns_size_18(self) -> None:
        """Bust == 107 → size 18 (upper bound of 103–107 range)."""
        assert derive_size_label(107.0) == "18"

    def test_exactly_108_returns_size_20(self) -> None:
        """Bust == 108 → size 20."""
        assert derive_size_label(108.0) == "20"

    def test_exactly_112_returns_size_20(self) -> None:
        """Bust == 112 → size 20 (upper bound of 108–112 range)."""
        assert derive_size_label(112.0) == "20"

    def test_exactly_113_returns_size_22w(self) -> None:
        """Bust == 113 → size 22W."""
        assert derive_size_label(113.0) == "22W"

    def test_exactly_117_returns_size_22w(self) -> None:
        """Bust == 117 → size 22W (upper bound of 113–117 range)."""
        assert derive_size_label(117.0) == "22W"

    def test_exactly_118_returns_size_24w(self) -> None:
        """Bust == 118 → size 24W."""
        assert derive_size_label(118.0) == "24W"

    def test_exactly_122_returns_size_24w(self) -> None:
        """Bust == 122 → size 24W (upper bound of 118–122 range)."""
        assert derive_size_label(122.0) == "24W"

    def test_exactly_123_returns_size_26w_plus(self) -> None:
        """Bust == 123 → size 26W+ (at the >= 123 boundary)."""
        assert derive_size_label(123.0) == "26W+"

    def test_above_123_returns_size_26w_plus(self) -> None:
        """Bust >> 123 → size 26W+."""
        assert derive_size_label(200.0) == "26W+"

    def test_spec_example_96_returns_size_14(self) -> None:
        """Spec states bust_cm=96 → size_label='14'."""
        assert derive_size_label(96.0) == "14"


# ---------------------------------------------------------------------------
# Unit tests: Measurements Pydantic model validation
# ---------------------------------------------------------------------------


class TestMeasurementsModel:
    """Test that the Measurements model enforces field ranges."""

    def _valid_payload(self) -> dict:
        return {
            "bust_cm": 96.0,
            "high_bust_cm": 85.0,
            "apex_to_apex_cm": 18.0,
            "waist_cm": 78.0,
            "hip_cm": 104.0,
            "height_cm": 168.0,
            "back_length_cm": 39.5,
        }

    # bust_cm: ge=60, le=200
    def test_bust_at_min_is_valid(self) -> None:
        data = self._valid_payload()
        data["bust_cm"] = 60.0
        m = Measurements(**data)
        assert m.bust_cm == 60.0

    def test_bust_at_max_is_valid(self) -> None:
        data = self._valid_payload()
        data["bust_cm"] = 200.0
        m = Measurements(**data)
        assert m.bust_cm == 200.0

    def test_bust_below_min_raises(self) -> None:
        data = self._valid_payload()
        data["bust_cm"] = 59.9
        with pytest.raises(ValidationError):
            Measurements(**data)

    def test_bust_above_max_raises(self) -> None:
        data = self._valid_payload()
        data["bust_cm"] = 200.1
        with pytest.raises(ValidationError):
            Measurements(**data)

    # waist_cm: ge=40, le=200
    def test_waist_at_min_is_valid(self) -> None:
        data = self._valid_payload()
        data["waist_cm"] = 40.0
        m = Measurements(**data)
        assert m.waist_cm == 40.0

    def test_waist_at_max_is_valid(self) -> None:
        data = self._valid_payload()
        data["waist_cm"] = 200.0
        m = Measurements(**data)
        assert m.waist_cm == 200.0

    def test_waist_below_min_raises(self) -> None:
        data = self._valid_payload()
        data["waist_cm"] = 39.9
        with pytest.raises(ValidationError):
            Measurements(**data)

    def test_waist_above_max_raises(self) -> None:
        data = self._valid_payload()
        data["waist_cm"] = 200.1
        with pytest.raises(ValidationError):
            Measurements(**data)

    # hip_cm: ge=60, le=200
    def test_hip_at_min_is_valid(self) -> None:
        data = self._valid_payload()
        data["hip_cm"] = 60.0
        m = Measurements(**data)
        assert m.hip_cm == 60.0

    def test_hip_at_max_is_valid(self) -> None:
        data = self._valid_payload()
        data["hip_cm"] = 200.0
        m = Measurements(**data)
        assert m.hip_cm == 200.0

    def test_hip_below_min_raises(self) -> None:
        data = self._valid_payload()
        data["hip_cm"] = 59.9
        with pytest.raises(ValidationError):
            Measurements(**data)

    def test_hip_above_max_raises(self) -> None:
        data = self._valid_payload()
        data["hip_cm"] = 200.1
        with pytest.raises(ValidationError):
            Measurements(**data)

    # height_cm: ge=120, le=220
    def test_height_at_min_is_valid(self) -> None:
        data = self._valid_payload()
        data["height_cm"] = 120.0
        m = Measurements(**data)
        assert m.height_cm == 120.0

    def test_height_at_max_is_valid(self) -> None:
        data = self._valid_payload()
        data["height_cm"] = 220.0
        m = Measurements(**data)
        assert m.height_cm == 220.0

    def test_height_below_min_raises(self) -> None:
        data = self._valid_payload()
        data["height_cm"] = 119.9
        with pytest.raises(ValidationError):
            Measurements(**data)

    def test_height_above_max_raises(self) -> None:
        data = self._valid_payload()
        data["height_cm"] = 220.1
        with pytest.raises(ValidationError):
            Measurements(**data)

    # back_length_cm: ge=30, le=60
    def test_back_length_at_min_is_valid(self) -> None:
        data = self._valid_payload()
        data["back_length_cm"] = 30.0
        m = Measurements(**data)
        assert m.back_length_cm == 30.0

    def test_back_length_at_max_is_valid(self) -> None:
        data = self._valid_payload()
        data["back_length_cm"] = 60.0
        m = Measurements(**data)
        assert m.back_length_cm == 60.0

    def test_back_length_below_min_raises(self) -> None:
        data = self._valid_payload()
        data["back_length_cm"] = 29.9
        with pytest.raises(ValidationError):
            Measurements(**data)

    def test_back_length_above_max_raises(self) -> None:
        data = self._valid_payload()
        data["back_length_cm"] = 60.1
        with pytest.raises(ValidationError):
            Measurements(**data)


# ---------------------------------------------------------------------------
# Integration tests: POST /measurements via TestClient
# ---------------------------------------------------------------------------


class TestMeasurementsRoute:
    """Integration tests for POST /measurements."""

    def _valid_body(self) -> dict:
        return {
            "bust_cm": 96.0,
            "high_bust_cm": 85.0,
            "apex_to_apex_cm": 18.0,
            "waist_cm": 78.0,
            "hip_cm": 104.0,
            "height_cm": 168.0,
            "back_length_cm": 39.5,
        }

    # AC: valid body returns 200 with all fields echoed + size_label
    def test_valid_body_returns_200(self) -> None:
        response = client.post("/measurements", json=self._valid_body())
        assert response.status_code == 200

    def test_valid_body_echoes_all_fields(self) -> None:
        response = client.post("/measurements", json=self._valid_body())
        body = response.json()
        assert body["bust_cm"] == 96.0
        assert body["waist_cm"] == 78.0
        assert body["hip_cm"] == 104.0
        assert body["height_cm"] == 168.0
        assert body["back_length_cm"] == 39.5

    def test_valid_body_includes_size_label(self) -> None:
        response = client.post("/measurements", json=self._valid_body())
        body = response.json()
        assert "size_label" in body

    # AC: bust_cm=96 → size_label="14"
    def test_spec_example_returns_size_14(self) -> None:
        response = client.post("/measurements", json=self._valid_body())
        assert response.json()["size_label"] == "14"

    # AC: plus-size bust → W label
    def test_plus_size_bust_returns_w_label(self) -> None:
        body = self._valid_body()
        body["bust_cm"] = 115.0  # falls in 113–117 → "22W"
        response = client.post("/measurements", json=body)
        assert response.status_code == 200
        assert response.json()["size_label"] == "22W"

    # AC: bust_cm below minimum → 422
    def test_bust_below_min_returns_422(self) -> None:
        body = self._valid_body()
        body["bust_cm"] = 59.0
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    def test_bust_below_min_error_references_bust_cm(self) -> None:
        body = self._valid_body()
        body["bust_cm"] = 59.0
        response = client.post("/measurements", json=body)
        assert response.status_code == 422
        detail = response.json()["detail"]
        fields = [err["loc"][-1] for err in detail]
        assert "bust_cm" in fields

    # AC: bust_cm above maximum → 422
    def test_bust_above_max_returns_422(self) -> None:
        body = self._valid_body()
        body["bust_cm"] = 201.0
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    # AC: missing waist_cm → 422
    def test_missing_waist_returns_422(self) -> None:
        body = self._valid_body()
        del body["waist_cm"]
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    # Each field missing individually → 422
    def test_missing_bust_returns_422(self) -> None:
        body = self._valid_body()
        del body["bust_cm"]
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    def test_missing_hip_returns_422(self) -> None:
        body = self._valid_body()
        del body["hip_cm"]
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    def test_missing_height_returns_422(self) -> None:
        body = self._valid_body()
        del body["height_cm"]
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    def test_missing_back_length_returns_422(self) -> None:
        body = self._valid_body()
        del body["back_length_cm"]
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    # Each field out of range → 422
    def test_waist_below_min_returns_422(self) -> None:
        body = self._valid_body()
        body["waist_cm"] = 39.0
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    def test_hip_below_min_returns_422(self) -> None:
        body = self._valid_body()
        body["hip_cm"] = 59.0
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    def test_height_below_min_returns_422(self) -> None:
        body = self._valid_body()
        body["height_cm"] = 119.0
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    def test_back_length_above_max_returns_422(self) -> None:
        body = self._valid_body()
        body["back_length_cm"] = 61.0
        response = client.post("/measurements", json=body)
        assert response.status_code == 422

    def test_empty_body_returns_422(self) -> None:
        response = client.post("/measurements", json={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Spec 07 — FBA fields (high_bust_cm, apex_to_apex_cm) and measurement_id
# ---------------------------------------------------------------------------


class TestFBAFields:
    """Tests for the two new FBA measurement fields added in spec 07."""

    def _valid_body(self) -> dict:
        return {
            "bust_cm": 96.0,
            "high_bust_cm": 85.0,
            "apex_to_apex_cm": 18.0,
            "waist_cm": 78.0,
            "hip_cm": 104.0,
            "height_cm": 168.0,
            "back_length_cm": 39.5,
        }

    # high_bust_cm validation
    def test_high_bust_cm_missing_returns_422(self) -> None:
        body = self._valid_body()
        del body["high_bust_cm"]
        assert client.post("/measurements", json=body).status_code == 422

    def test_high_bust_cm_at_min_is_valid(self) -> None:
        body = self._valid_body()
        body["high_bust_cm"] = 60.0
        assert client.post("/measurements", json=body).status_code == 200

    def test_high_bust_cm_at_max_is_valid(self) -> None:
        body = self._valid_body()
        body["high_bust_cm"] = 200.0
        assert client.post("/measurements", json=body).status_code == 200

    def test_high_bust_cm_below_min_returns_422(self) -> None:
        body = self._valid_body()
        body["high_bust_cm"] = 59.9
        resp = client.post("/measurements", json=body)
        assert resp.status_code == 422
        fields = [err["loc"][-1] for err in resp.json()["detail"]]
        assert "high_bust_cm" in fields

    def test_high_bust_cm_above_max_returns_422(self) -> None:
        body = self._valid_body()
        body["high_bust_cm"] = 200.1
        assert client.post("/measurements", json=body).status_code == 422

    # apex_to_apex_cm validation
    def test_apex_to_apex_cm_missing_returns_422(self) -> None:
        body = self._valid_body()
        del body["apex_to_apex_cm"]
        assert client.post("/measurements", json=body).status_code == 422

    def test_apex_to_apex_cm_at_min_is_valid(self) -> None:
        body = self._valid_body()
        body["apex_to_apex_cm"] = 10.0
        assert client.post("/measurements", json=body).status_code == 200

    def test_apex_to_apex_cm_at_max_is_valid(self) -> None:
        body = self._valid_body()
        body["apex_to_apex_cm"] = 30.0
        assert client.post("/measurements", json=body).status_code == 200

    def test_apex_to_apex_cm_below_min_returns_422(self) -> None:
        body = self._valid_body()
        body["apex_to_apex_cm"] = 9.9
        resp = client.post("/measurements", json=body)
        assert resp.status_code == 422
        fields = [err["loc"][-1] for err in resp.json()["detail"]]
        assert "apex_to_apex_cm" in fields

    def test_apex_to_apex_cm_above_max_returns_422(self) -> None:
        body = self._valid_body()
        body["apex_to_apex_cm"] = 30.1
        assert client.post("/measurements", json=body).status_code == 422

    # Response shape
    def test_valid_body_echoes_fba_fields(self) -> None:
        resp = client.post("/measurements", json=self._valid_body())
        assert resp.status_code == 200
        data = resp.json()
        assert data["high_bust_cm"] == 85.0
        assert data["apex_to_apex_cm"] == 18.0


class TestMeasurementId:
    """Tests for measurement_id session store (spec 07)."""

    def _valid_body(self) -> dict:
        return {
            "bust_cm": 96.0,
            "high_bust_cm": 85.0,
            "apex_to_apex_cm": 18.0,
            "waist_cm": 78.0,
            "hip_cm": 104.0,
            "height_cm": 168.0,
            "back_length_cm": 39.5,
        }

    def test_response_includes_measurement_id(self) -> None:
        resp = client.post("/measurements", json=self._valid_body())
        assert resp.status_code == 200
        assert "measurement_id" in resp.json()

    def test_measurement_id_is_uuid_string(self) -> None:
        resp = client.post("/measurements", json=self._valid_body())
        mid = resp.json()["measurement_id"]
        assert isinstance(mid, str)
        assert len(mid) == 36  # standard UUID format: 8-4-4-4-12

    def test_two_posts_have_distinct_ids_and_isolated_data(self) -> None:
        from lib.measurements import get_measurements

        body1 = self._valid_body()
        body2 = {**self._valid_body(), "bust_cm": 88.0, "high_bust_cm": 80.0}
        r1 = client.post("/measurements", json=body1)
        r2 = client.post("/measurements", json=body2)
        mid1, mid2 = r1.json()["measurement_id"], r2.json()["measurement_id"]
        assert mid1 != mid2
        # Each UUID retrieves its own data
        assert get_measurements(mid1).bust_cm == 96.0
        assert get_measurements(mid2).bust_cm == 88.0

    def test_store_roundtrip_via_get_measurements(self) -> None:
        from lib.measurements import get_measurements

        resp = client.post("/measurements", json=self._valid_body())
        mid = resp.json()["measurement_id"]
        stored = get_measurements(mid)
        assert stored.bust_cm == 96.0
        assert stored.high_bust_cm == 85.0
        assert stored.apex_to_apex_cm == 18.0
        # The stored object's measurement_id must match the retrieval key
        assert stored.measurement_id == mid

    def test_get_measurements_unknown_id_raises_key_error(self) -> None:
        from lib.measurements import get_measurements

        with pytest.raises(KeyError):
            get_measurements("00000000-0000-0000-0000-000000000000")
