"""Unit tests for backend/lib/photos/ — validate, store, resolve helpers.

All tests in this file work without any FastAPI imports (import hygiene requirement).
"""

import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers: minimal valid JPEG / PNG bytes
# ---------------------------------------------------------------------------


def make_jpeg_bytes(size_bytes: int = 100) -> bytes:
    """Return JPEG-magic-byte header padded to size_bytes."""
    header = bytes([0xFF, 0xD8, 0xFF, 0xE0]) + b"\x00" * (size_bytes - 4)
    return header


def make_png_bytes(size_bytes: int = 100) -> bytes:
    """Return PNG-magic-byte header padded to size_bytes."""
    header = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b"\x00" * (size_bytes - 8)
    return header


def make_gif_bytes(size_bytes: int = 100) -> bytes:
    """Return GIF-magic-byte header padded to size_bytes."""
    header = b"GIF89a" + b"\x00" * (size_bytes - 6)
    return header


MB = 1024 * 1024


# ---------------------------------------------------------------------------
# Import-hygiene test
# ---------------------------------------------------------------------------


class TestImportHygiene:
    """Ensure lib/photos/ has no FastAPI imports."""

    def _source_files(self) -> list[Path]:
        base = Path(__file__).parent.parent / "lib" / "photos"
        return list(base.glob("*.py"))

    def test_no_fastapi_in_source_files(self) -> None:
        """lib/photos/*.py must not import fastapi."""
        for path in self._source_files():
            text = path.read_text()
            assert (
                "fastapi" not in text
            ), f"{path.name} contains 'fastapi' — lib modules must be framework-free"


# ---------------------------------------------------------------------------
# validate_photo tests
# ---------------------------------------------------------------------------


class TestValidatePhoto:
    """Tests for validate_photo(file_bytes, filename) in lib/photos/validate.py."""

    def test_valid_jpeg_does_not_raise(self) -> None:
        """A JPEG file with correct magic bytes returns without raising."""
        from lib.photos.validate import validate_photo

        validate_photo(make_jpeg_bytes(1000), "front.jpg")

    def test_valid_png_does_not_raise(self) -> None:
        """A PNG file with correct magic bytes returns without raising."""
        from lib.photos.validate import validate_photo

        validate_photo(make_png_bytes(1000), "front.png")

    def test_jpeg_magic_with_jpeg_ext_is_valid(self) -> None:
        """JPEG magic bytes + .jpeg extension is accepted."""
        from lib.photos.validate import validate_photo

        validate_photo(make_jpeg_bytes(500), "photo.jpeg")

    def test_png_magic_with_png_ext_is_valid(self) -> None:
        """PNG magic bytes + .PNG extension (case-insensitive) is accepted."""
        from lib.photos.validate import validate_photo

        validate_photo(make_png_bytes(500), "photo.PNG")

    def test_oversized_file_raises_photo_validation_error(self) -> None:
        """A file > 10 MB raises PhotoTooLargeError."""
        from lib.photos.validate import PhotoTooLargeError, validate_photo

        oversized = make_jpeg_bytes(10 * MB + 1)
        with pytest.raises(PhotoTooLargeError):
            validate_photo(oversized, "big.jpg")

    def test_oversized_error_mentions_size_limit(self) -> None:
        """PhotoTooLargeError message mentions size limit."""
        from lib.photos.validate import PhotoTooLargeError, validate_photo

        oversized = make_jpeg_bytes(10 * MB + 1)
        with pytest.raises(PhotoTooLargeError, match=r"10"):
            validate_photo(oversized, "big.jpg")

    def test_exactly_10mb_does_not_raise(self) -> None:
        """Exactly 10 MB is allowed (limit is strictly greater than)."""
        from lib.photos.validate import validate_photo

        exactly_10mb = make_jpeg_bytes(10 * MB)
        validate_photo(exactly_10mb, "exactly10.jpg")

    def test_png_bytes_with_jpg_extension_raises_mime_error(self) -> None:
        """PNG magic bytes but .jpg extension raises PhotoInvalidTypeError."""
        from lib.photos.validate import PhotoInvalidTypeError, validate_photo

        png_data = make_png_bytes(1000)
        with pytest.raises(PhotoInvalidTypeError):
            validate_photo(png_data, "sneaky.jpg")

    def test_jpeg_bytes_with_png_extension_raises_mime_error(self) -> None:
        """JPEG magic bytes but .png extension raises PhotoInvalidTypeError."""
        from lib.photos.validate import PhotoInvalidTypeError, validate_photo

        jpeg_data = make_jpeg_bytes(1000)
        with pytest.raises(PhotoInvalidTypeError):
            validate_photo(jpeg_data, "sneaky.png")

    def test_gif_file_raises_mime_error(self) -> None:
        """GIF magic bytes with any extension raises PhotoInvalidTypeError."""
        from lib.photos.validate import PhotoInvalidTypeError, validate_photo

        gif_data = make_gif_bytes(500)
        with pytest.raises(PhotoInvalidTypeError):
            validate_photo(gif_data, "anim.gif")

    def test_mime_error_mentions_jpeg_and_png(self) -> None:
        """PhotoInvalidTypeError message references JPEG and PNG."""
        from lib.photos.validate import PhotoInvalidTypeError, validate_photo

        gif_data = make_gif_bytes(500)
        with pytest.raises(PhotoInvalidTypeError, match=r"(?i)jpeg|png"):
            validate_photo(gif_data, "anim.gif")

    def test_photo_invalid_type_error_is_subclass_of_photo_validation_error(self) -> None:
        """PhotoInvalidTypeError subclasses PhotoValidationError."""
        from lib.photos.validate import PhotoInvalidTypeError, PhotoValidationError

        assert issubclass(PhotoInvalidTypeError, PhotoValidationError)

    def test_photo_too_large_error_is_subclass_of_photo_validation_error(self) -> None:
        """PhotoTooLargeError subclasses PhotoValidationError."""
        from lib.photos.validate import PhotoTooLargeError, PhotoValidationError

        assert issubclass(PhotoTooLargeError, PhotoValidationError)

    def test_size_checked_before_mime(self) -> None:
        """If file is both oversized AND wrong type, PhotoTooLargeError is raised (size checked first)."""
        from lib.photos.validate import PhotoTooLargeError, validate_photo

        big_gif = make_gif_bytes(10 * MB + 1)
        with pytest.raises(PhotoTooLargeError):
            validate_photo(big_gif, "big.gif")


# ---------------------------------------------------------------------------
# store_photo / resolve_photo_path tests
# ---------------------------------------------------------------------------


class TestStoreAndResolve:
    """Tests for store_photo and resolve_photo_path in lib/photos/store.py."""

    def test_store_photo_creates_file_on_disk(self, tmp_path: Path) -> None:
        """store_photo writes the bytes to disk at the expected location."""
        from lib.photos.store import store_photo

        measurement_id = str(uuid.uuid4())
        photo_id = str(uuid.uuid4())
        file_bytes = make_jpeg_bytes(200)
        store_photo(measurement_id, photo_id, file_bytes, ".jpg", base_dir=tmp_path)

        stored_path = tmp_path / "photos" / measurement_id / f"{photo_id}.jpg"
        assert stored_path.exists()
        assert stored_path.read_bytes() == file_bytes

    def test_resolve_photo_path_returns_existing_path(self, tmp_path: Path) -> None:
        """resolve_photo_path returns a path that exists after a store_photo call."""
        from lib.photos.store import resolve_photo_path, store_photo

        measurement_id = str(uuid.uuid4())
        photo_id = str(uuid.uuid4())
        file_bytes = make_jpeg_bytes(200)
        store_photo(measurement_id, photo_id, file_bytes, ".jpg", base_dir=tmp_path)

        resolved = resolve_photo_path(measurement_id, photo_id, base_dir=tmp_path)
        assert resolved.exists()
        assert resolved.read_bytes() == file_bytes

    def test_resolve_photo_path_raises_for_unknown_photo_id(self, tmp_path: Path) -> None:
        """resolve_photo_path raises FileNotFoundError for unknown photo_id."""
        from lib.photos.store import resolve_photo_path

        with pytest.raises(FileNotFoundError):
            resolve_photo_path("nonexistent-measurement", "nonexistent-photo", base_dir=tmp_path)

    def test_store_photo_creates_parent_directories(self, tmp_path: Path) -> None:
        """store_photo creates missing parent directories automatically."""
        from lib.photos.store import store_photo

        measurement_id = str(uuid.uuid4())
        photo_id = str(uuid.uuid4())
        # Confirm parent dir does not exist yet
        parent = tmp_path / "photos" / measurement_id
        assert not parent.exists()

        store_photo(measurement_id, photo_id, make_jpeg_bytes(100), ".jpg", base_dir=tmp_path)

        assert parent.exists()

    def test_resolve_photo_path_works_with_png_extension(self, tmp_path: Path) -> None:
        """resolve_photo_path handles .png extension via glob."""
        from lib.photos.store import resolve_photo_path, store_photo

        measurement_id = str(uuid.uuid4())
        photo_id = str(uuid.uuid4())
        store_photo(measurement_id, photo_id, make_png_bytes(100), ".png", base_dir=tmp_path)

        resolved = resolve_photo_path(measurement_id, photo_id, base_dir=tmp_path)
        assert resolved.suffix == ".png"
        assert resolved.exists()

    def test_store_photo_returns_path(self, tmp_path: Path) -> None:
        """store_photo returns the Path where the file was stored."""
        from lib.photos.store import store_photo

        measurement_id = str(uuid.uuid4())
        photo_id = str(uuid.uuid4())
        result = store_photo(
            measurement_id, photo_id, make_jpeg_bytes(100), ".jpg", base_dir=tmp_path
        )

        assert isinstance(result, Path)
        assert result.exists()
