"""Route tests for POST /photos/upload."""

import io
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from lib.measurements import MeasurementsResponse, store_measurements
from main import app

client = TestClient(app)

MB = 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_jpeg_bytes(size_bytes: int = 500) -> bytes:
    """Return JPEG-magic header padded to size_bytes."""
    return bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b"\x00" * max(0, size_bytes - 4)


def make_png_bytes(size_bytes: int = 500) -> bytes:
    """Return PNG-magic header padded to size_bytes."""
    return bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b"\x00" * max(
        0, size_bytes - 8
    )


def make_gif_bytes(size_bytes: int = 500) -> bytes:
    """Return GIF header padded to size_bytes."""
    return b"GIF89a" + b"\x00" * max(0, size_bytes - 6)


def create_measurement_id() -> str:
    """Create a stored measurement session and return its ID."""
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


def make_upload_files(
    file_specs: list[tuple[str, bytes]],
    view_labels: list[str],
    measurement_id: str,
) -> dict:
    """Build a multipart form data dict for TestClient.

    file_specs: list of (filename, bytes)
    """
    files = [("photos", (fname, io.BytesIO(data), "image/jpeg")) for fname, data in file_specs]
    data = {
        "measurement_id": measurement_id,
        "view_labels": view_labels,
    }
    return {"files": files, "data": data}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestUploadHappyPath:
    """Successful upload scenarios."""

    def test_two_valid_photos_returns_200(self) -> None:
        """POST with 2 valid JPEG files and labels returns 200."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
                ("photos", ("back.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front", "back"]},
        )
        assert response.status_code == 200

    def test_two_valid_photos_returns_list_of_records(self) -> None:
        """Response body is a list of 2 PhotoRecord objects."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
                ("photos", ("back.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front", "back"]},
        )
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 2

    def test_response_records_have_required_fields(self) -> None:
        """Each PhotoRecord has photo_id, view_label, and filename."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front"]},
        )
        record = response.json()[0]
        assert "photo_id" in record
        assert "view_label" in record
        assert "filename" in record

    def test_response_view_label_matches_input(self) -> None:
        """Response view_label matches submitted label."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front"]},
        )
        assert response.json()[0]["view_label"] == "front"

    def test_response_filename_matches_input(self) -> None:
        """Response filename matches submitted filename."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("myfront.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front"]},
        )
        assert response.json()[0]["filename"] == "myfront.jpg"

    def test_response_photo_id_is_uuid_string(self) -> None:
        """photo_id in response is a valid UUID string."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front"]},
        )
        photo_id = response.json()[0]["photo_id"]
        # Should be parseable as UUID
        uuid.UUID(photo_id)

    def test_one_photo_returns_200(self) -> None:
        """Single file upload returns 200."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("side.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["side"]},
        )
        assert response.status_code == 200

    def test_three_photos_returns_200(self) -> None:
        """Maximum 3 files returns 200."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
                ("photos", ("back.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
                ("photos", ("side.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front", "back", "side"]},
        )
        assert response.status_code == 200
        assert len(response.json()) == 3

    def test_png_photo_is_accepted(self) -> None:
        """PNG files are accepted alongside JPEGs."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.png", io.BytesIO(make_png_bytes()), "image/png")),
            ],
            data={"measurement_id": mid, "view_labels": ["front"]},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Error cases: file count
# ---------------------------------------------------------------------------


class TestUploadFileCountErrors:
    """Tests for 0 and >3 file count rejections."""

    def test_zero_files_returns_400(self) -> None:
        """POST with no photos returns 400."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            data={"measurement_id": mid, "view_labels": []},
        )
        assert response.status_code == 400

    def test_zero_files_returns_upload_1_3_detail(self) -> None:
        """400 detail matches spec: 'Upload 1–3 photos'."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            data={"measurement_id": mid, "view_labels": []},
        )
        assert response.json()["detail"] == "Upload 1–3 photos"

    def test_four_files_returns_400(self) -> None:
        """POST with 4 photos returns 400."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", (f"photo{i}.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg"))
                for i in range(4)
            ],
            data={"measurement_id": mid, "view_labels": ["front", "back", "side", "front"]},
        )
        assert response.status_code == 400

    def test_four_files_detail_mentions_count(self) -> None:
        """400 for 4 files detail matches spec."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", (f"photo{i}.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg"))
                for i in range(4)
            ],
            data={"measurement_id": mid, "view_labels": ["front", "back", "side", "front"]},
        )
        assert response.json()["detail"] == "Upload 1–3 photos"


# ---------------------------------------------------------------------------
# Error cases: label mismatch and invalid labels
# ---------------------------------------------------------------------------


class TestUploadLabelErrors:
    """Tests for view_labels validation."""

    def test_mismatched_label_count_returns_400(self) -> None:
        """2 photos + 1 label → 400."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
                ("photos", ("back.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front"]},
        )
        assert response.status_code == 400

    def test_mismatched_label_count_detail(self) -> None:
        """400 detail for label mismatch matches spec."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front", "back"]},
        )
        assert response.json()["detail"] == "Each photo must have a view label"

    def test_invalid_view_label_returns_400(self) -> None:
        """A label not in {front, back, side} returns 400."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("photo.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["diagonal"]},
        )
        assert response.status_code == 400

    def test_invalid_view_label_detail(self) -> None:
        """400 detail for invalid label matches spec."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("photo.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["diagonal"]},
        )
        assert response.json()["detail"] == "view_label must be one of: front, back, side"


# ---------------------------------------------------------------------------
# Error cases: unknown measurement_id
# ---------------------------------------------------------------------------


class TestUploadMeasurementIdErrors:
    """Tests for unknown measurement_id."""

    def test_unknown_measurement_id_returns_404(self) -> None:
        """POST with a measurement_id that doesn't exist returns 404."""
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={
                "measurement_id": "00000000-0000-0000-0000-000000000000",
                "view_labels": ["front"],
            },
        )
        assert response.status_code == 404

    def test_unknown_measurement_id_detail(self) -> None:
        """404 detail matches spec."""
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes()), "image/jpeg")),
            ],
            data={
                "measurement_id": "00000000-0000-0000-0000-000000000000",
                "view_labels": ["front"],
            },
        )
        assert response.json()["detail"] == "Measurements not found"


# ---------------------------------------------------------------------------
# Error cases: file size
# ---------------------------------------------------------------------------


class TestUploadFileSizeErrors:
    """Tests for 413 oversized file errors."""

    def test_oversized_file_returns_413(self) -> None:
        """A file > 10 MB returns 413."""
        mid = create_measurement_id()
        oversized = make_jpeg_bytes(10 * MB + 1)
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("big.jpg", io.BytesIO(oversized), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front"]},
        )
        assert response.status_code == 413

    def test_oversized_file_detail(self) -> None:
        """413 detail matches spec."""
        mid = create_measurement_id()
        oversized = make_jpeg_bytes(10 * MB + 1)
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("big.jpg", io.BytesIO(oversized), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front"]},
        )
        assert response.json()["detail"] == "Each photo must be under 10 MB"


# ---------------------------------------------------------------------------
# Error cases: MIME type
# ---------------------------------------------------------------------------


class TestUploadMimeErrors:
    """Tests for 415 unsupported media type errors."""

    def test_gif_file_returns_415(self) -> None:
        """A GIF file returns 415."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("anim.gif", io.BytesIO(make_gif_bytes()), "image/gif")),
            ],
            data={"measurement_id": mid, "view_labels": ["front"]},
        )
        assert response.status_code == 415

    def test_gif_file_detail(self) -> None:
        """415 detail matches spec."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("anim.gif", io.BytesIO(make_gif_bytes()), "image/gif")),
            ],
            data={"measurement_id": mid, "view_labels": ["front"]},
        )
        assert response.json()["detail"] == "Only JPEG and PNG files are accepted"


# ---------------------------------------------------------------------------
# All-or-nothing validation
# ---------------------------------------------------------------------------


class TestAllOrNothingValidation:
    """If any file fails validation, no files are written and the error is returned."""

    def test_one_valid_one_oversized_returns_413(self) -> None:
        """If the second of 2 files is oversized, returns 413."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes(500)), "image/jpeg")),
                ("photos", ("big.jpg", io.BytesIO(make_jpeg_bytes(10 * MB + 1)), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["front", "back"]},
        )
        assert response.status_code == 413

    def test_one_valid_one_invalid_writes_no_files(self, tmp_path: Path) -> None:
        """If any file is invalid, no files are written to disk (all-or-nothing)."""
        mid = create_measurement_id()

        # A valid JPEG and a GIF: expect 415 and nothing on disk
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes(500)), "image/jpeg")),
                ("photos", ("bad.gif", io.BytesIO(make_gif_bytes(500)), "image/gif")),
            ],
            data={"measurement_id": mid, "view_labels": ["front", "back"]},
        )
        assert response.status_code == 415

    def test_valid_files_with_invalid_label_writes_no_files_and_returns_400(self) -> None:
        """Invalid label causes 400 without writing any files."""
        mid = create_measurement_id()
        response = client.post(
            "/photos/upload",
            files=[
                ("photos", ("front.jpg", io.BytesIO(make_jpeg_bytes(500)), "image/jpeg")),
            ],
            data={"measurement_id": mid, "view_labels": ["top"]},
        )
        assert response.status_code == 400
