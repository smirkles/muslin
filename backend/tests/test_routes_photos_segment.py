"""Route tests for POST /photos/{photo_id}/segment."""

import io
import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from lib.measurements import MeasurementsResponse, store_measurements
from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_png_bytes(width: int = 4, height: int = 4, mode: str = "RGB") -> bytes:
    img = Image.new(mode, (width, height), color=128)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def make_grayscale_mask_bytes() -> bytes:
    return make_png_bytes(mode="L")


def create_measurement_id() -> str:
    m = MeasurementsResponse(
        bust_cm=96.0,
        high_bust_cm=85.0,
        apex_to_apex_cm=18.0,
        waist_cm=78.0,
        hip_cm=104.0,
        height_cm=168.0,
        back_length_cm=39.5,
        measurement_id=str(uuid.uuid4()),
        size_label="14",
    )
    store_measurements(m)
    return m.measurement_id


def upload_photo(tmp_path: Path) -> tuple[str, str]:
    """Upload a photo and return (measurement_id, photo_id)."""
    mid = create_measurement_id()
    response = client.post(
        "/photos/upload",
        files=[("photos", ("front.png", io.BytesIO(make_png_bytes()), "image/png"))],
        data={"measurement_id": mid, "view_labels": ["front"]},
    )
    assert response.status_code == 200, response.text
    photo_id = response.json()[0]["photo_id"]
    return mid, photo_id


def _make_mock_segmenter(
    iou_score: float = 0.88,
    *,
    raise_exc: Exception | None = None,
) -> MagicMock:
    """Return a mock segmenter whose segment() produces a plausible SegmentationResult."""
    from lib.segmentation.segmenter import SegmentationResult

    mock = MagicMock()
    if raise_exc is not None:
        mock.segment.side_effect = raise_exc
    else:
        mock.segment.return_value = SegmentationResult(
            photo_id="fake-photo-id",
            mask_path=Path("/tmp/mask.png"),
            cropped_path=Path("/tmp/cropped.png"),
            confidence=iou_score,
        )
    return mock


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestSegmentHappyPath:
    """Successful segmentation scenarios."""

    def test_returns_200(self, tmp_path: Path) -> None:
        """Valid photo_id with mocked segmenter returns 200."""
        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter()
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
                resp = client.post(f"/photos/{photo_id}/segment")
        assert resp.status_code == 200

    def test_response_has_photo_id(self, tmp_path: Path) -> None:
        """Response body includes photo_id."""
        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter()
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
                resp = client.post(f"/photos/{photo_id}/segment")
        assert "photo_id" in resp.json()

    def test_response_has_mask_path(self, tmp_path: Path) -> None:
        """Response body includes mask_path."""
        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter()
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
                resp = client.post(f"/photos/{photo_id}/segment")
        assert "mask_path" in resp.json()

    def test_response_has_cropped_path(self, tmp_path: Path) -> None:
        """Response body includes cropped_path."""
        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter()
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
                resp = client.post(f"/photos/{photo_id}/segment")
        assert "cropped_path" in resp.json()

    def test_response_has_confidence(self, tmp_path: Path) -> None:
        """Response body includes confidence."""
        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter()
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
                resp = client.post(f"/photos/{photo_id}/segment")
        assert "confidence" in resp.json()

    def test_with_explicit_point_prompt_returns_200(self, tmp_path: Path) -> None:
        """Request body with point_prompt=[0.3, 0.7] returns 200."""
        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter()
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
                resp = client.post(
                    f"/photos/{photo_id}/segment",
                    json={"point_prompt": [0.3, 0.7]},
                )
        assert resp.status_code == 200

    def test_with_null_point_prompt_returns_200(self, tmp_path: Path) -> None:
        """Request body with point_prompt=null returns 200."""
        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter()
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
                resp = client.post(
                    f"/photos/{photo_id}/segment",
                    json={"point_prompt": None},
                )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestSegmentErrors:
    """Error scenarios for the segment endpoint."""

    def test_unknown_photo_id_returns_404(self) -> None:
        """photo_id that was never uploaded returns 404."""
        fake_id = str(uuid.uuid4())
        resp = client.post(f"/photos/{fake_id}/segment")
        assert resp.status_code == 404

    def test_unknown_photo_id_detail(self) -> None:
        """404 detail matches spec."""
        fake_id = str(uuid.uuid4())
        resp = client.post(f"/photos/{fake_id}/segment")
        assert resp.json()["detail"] == "Photo not found"

    def test_missing_replicate_token_returns_500(self, tmp_path: Path) -> None:
        """Missing REPLICATE_API_TOKEN returns 500."""
        from lib.segmentation.segmenter import ConfigError

        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter(raise_exc=ConfigError("REPLICATE_API_TOKEN not set"))
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            resp = client.post(f"/photos/{photo_id}/segment")
        assert resp.status_code == 500

    def test_missing_replicate_token_detail(self, tmp_path: Path) -> None:
        """500 detail matches spec."""
        from lib.segmentation.segmenter import ConfigError

        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter(raise_exc=ConfigError("REPLICATE_API_TOKEN not set"))
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            resp = client.post(f"/photos/{photo_id}/segment")
        assert resp.json()["detail"] == "REPLICATE_API_TOKEN not configured"

    def test_replicate_error_returns_502(self, tmp_path: Path) -> None:
        """Replicate SDK exception returns 502."""
        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter(raise_exc=RuntimeError("network failure"))
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            resp = client.post(f"/photos/{photo_id}/segment")
        assert resp.status_code == 502

    def test_replicate_error_detail_matches_spec(self, tmp_path: Path) -> None:
        """502 detail matches spec exactly."""
        mid, photo_id = upload_photo(tmp_path)
        mock_seg = _make_mock_segmenter(raise_exc=RuntimeError("network failure"))
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            resp = client.post(f"/photos/{photo_id}/segment")
        assert resp.json()["detail"] == "Segmentation service error"

    def test_replicate_error_does_not_leak_original_message(self, tmp_path: Path) -> None:
        """Original exception message is not exposed in the 502 response body."""
        mid, photo_id = upload_photo(tmp_path)
        secret_msg = "internal-secret-error-xyz"
        mock_seg = _make_mock_segmenter(raise_exc=RuntimeError(secret_msg))
        with patch("routes.photos.get_segmenter", return_value=mock_seg):
            resp = client.post(f"/photos/{photo_id}/segment")
        assert secret_msg not in resp.text
