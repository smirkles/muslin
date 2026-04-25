"""Unit tests for ReplicateSegmenter — all Replicate calls are mocked."""

import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from lib.segmentation.segmenter import ConfigError, SegmentationResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_png_bytes(width: int = 4, height: int = 4, mode: str = "RGB") -> bytes:
    """Return bytes of a valid PNG image."""
    img = Image.new(mode, (width, height), color=128)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def make_grayscale_mask_bytes(width: int = 4, height: int = 4) -> bytes:
    """Return bytes of a valid grayscale PNG (for use as mask)."""
    return make_png_bytes(width, height, mode="L")


@pytest.fixture()
def photo_file(tmp_path: Path) -> Path:
    """A real PNG on disk representing an uploaded photo."""
    path = tmp_path / "front.png"
    path.write_bytes(make_png_bytes())
    return path


def _make_replicate_output(iou_score: float = 0.92) -> dict:
    """Build a fake Replicate SAM-2 output dict with readable mask bytes."""
    mask_bytes = make_grayscale_mask_bytes()
    mask_mock = MagicMock()
    mask_mock.read.return_value = mask_bytes
    return {"masks": [mask_mock], "iou_score": iou_score}


# ---------------------------------------------------------------------------
# Model and point prompt tests
# ---------------------------------------------------------------------------


class TestSegmentCallsReplicate:
    """Verify the correct arguments are passed to replicate.run."""

    def test_calls_default_model(self, photo_file: Path) -> None:
        """segment() calls replicate.run with 'meta/sam-2' by default."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.return_value = _make_replicate_output()
                ReplicateSegmenter().segment(photo_file)

        mock_run.assert_called_once()
        model_arg = mock_run.call_args[0][0]
        assert model_arg == "meta/sam-2"

    def test_default_point_prompt_is_centre(self, photo_file: Path) -> None:
        """When point_prompt is None, the call uses [0.5, 0.5] as the foreground point."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.return_value = _make_replicate_output()
                ReplicateSegmenter().segment(photo_file)

        call_input = mock_run.call_args[1]["input"]
        # input_points is [[[x, y]]] — one point, one object
        assert call_input["input_points"] == [[[0.5, 0.5]]]
        assert call_input["input_labels"] == [[1]]

    def test_custom_point_prompt_is_passed_through(self, photo_file: Path) -> None:
        """Explicit point_prompt=(0.3, 0.7) is forwarded to Replicate."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.return_value = _make_replicate_output()
                ReplicateSegmenter().segment(photo_file, point_prompt=(0.3, 0.7))

        call_input = mock_run.call_args[1]["input"]
        assert call_input["input_points"] == [[[0.3, 0.7]]]

    def test_image_is_passed_as_base64_data_uri(self, photo_file: Path) -> None:
        """Image is encoded as a base64 data URI in the Replicate call."""
        import base64

        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.return_value = _make_replicate_output()
                ReplicateSegmenter().segment(photo_file)

        call_input = mock_run.call_args[1]["input"]
        image_arg = call_input["image"]
        assert image_arg.startswith("data:image/")
        # The base64 payload must decode back to the original file bytes
        b64_part = image_arg.split(",", 1)[1]
        assert base64.b64decode(b64_part) == photo_file.read_bytes()


# ---------------------------------------------------------------------------
# Result shape tests
# ---------------------------------------------------------------------------


class TestSegmentResult:
    """Verify the returned SegmentationResult has correct values and files."""

    def test_confidence_matches_iou_score(self, photo_file: Path) -> None:
        """SegmentationResult.confidence equals the iou_score from Replicate."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.return_value = _make_replicate_output(iou_score=0.92)
                result = ReplicateSegmenter().segment(photo_file)

        assert result.confidence == pytest.approx(0.92)

    def test_mask_path_exists_on_disk(self, photo_file: Path) -> None:
        """mask_path points to an existing file after segment() returns."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.return_value = _make_replicate_output()
                result = ReplicateSegmenter().segment(photo_file)

        assert result.mask_path.exists()

    def test_cropped_path_exists_on_disk(self, photo_file: Path) -> None:
        """cropped_path points to an existing file after segment() returns."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.return_value = _make_replicate_output()
                result = ReplicateSegmenter().segment(photo_file)

        assert result.cropped_path.exists()

    def test_result_is_segmentation_result_instance(self, photo_file: Path) -> None:
        """Return type is a SegmentationResult dataclass."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.return_value = _make_replicate_output()
                result = ReplicateSegmenter().segment(photo_file)

        assert isinstance(result, SegmentationResult)

    def test_photo_id_in_result_matches_file_stem(self, photo_file: Path) -> None:
        """SegmentationResult.photo_id equals the photo file stem."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.return_value = _make_replicate_output()
                result = ReplicateSegmenter().segment(photo_file)

        assert result.photo_id == photo_file.stem


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestSegmentErrors:
    """Verify error conditions raise the right exceptions."""

    def test_missing_token_raises_config_error(self, photo_file: Path) -> None:
        """ConfigError is raised when REPLICATE_API_TOKEN is not set."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        env_without_token = {k: v for k, v in os.environ.items() if k != "REPLICATE_API_TOKEN"}
        with patch.dict(os.environ, env_without_token, clear=True):
            with pytest.raises(ConfigError) as exc_info:
                ReplicateSegmenter().segment(photo_file)

        assert "REPLICATE_API_TOKEN" in str(exc_info.value)

    def test_replicate_exception_propagates(self, photo_file: Path) -> None:
        """Exceptions from replicate.run propagate to the caller (not swallowed)."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.side_effect = RuntimeError("Replicate exploded")
                with pytest.raises(RuntimeError, match="Replicate exploded"):
                    ReplicateSegmenter().segment(photo_file)

    def test_empty_masks_raises_runtime_error(self, photo_file: Path) -> None:
        """RuntimeError is raised when Replicate returns an empty masks list."""
        from lib.segmentation.replicate_segmenter import ReplicateSegmenter

        with patch.dict(os.environ, {"REPLICATE_API_TOKEN": "test-token"}):
            with patch("lib.segmentation.replicate_segmenter.replicate.run") as mock_run:
                mock_run.return_value = {"masks": [], "iou_score": 0.0}
                with pytest.raises(RuntimeError, match="no masks"):
                    ReplicateSegmenter().segment(photo_file)


# ---------------------------------------------------------------------------
# Import hygiene
# ---------------------------------------------------------------------------


class TestImportHygiene:
    """lib/segmentation/ must not import FastAPI or any HTTP framework."""

    def test_segmentation_lib_has_no_fastapi_imports(self) -> None:
        """No file in lib/segmentation/ imports fastapi."""
        lib_dir = Path(__file__).parent.parent / "lib" / "segmentation"
        for py_file in lib_dir.rglob("*.py"):
            content = py_file.read_text()
            assert (
                "fastapi" not in content
            ), f"{py_file.name} imports fastapi — lib/ must have no HTTP framework imports"


# ---------------------------------------------------------------------------
# Live smoke test (skipped unless REPLICATE_API_TOKEN is set)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_live_smoke_test(tmp_path: Path) -> None:
    """Calls the real Replicate API with a test image. Skipped if no token."""
    if not os.environ.get("REPLICATE_API_TOKEN"):
        pytest.skip("REPLICATE_API_TOKEN not set — skipping live smoke test")

    from lib.segmentation.replicate_segmenter import ReplicateSegmenter

    photo_path = tmp_path / "test_photo.png"
    photo_path.write_bytes(make_png_bytes(64, 64))

    result = ReplicateSegmenter().segment(photo_path)

    assert result.mask_path.exists()
    assert result.mask_path.stat().st_size > 0
    assert result.cropped_path.exists()
    assert 0.0 <= result.confidence <= 1.0
