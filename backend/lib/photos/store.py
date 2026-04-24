"""Photo storage helpers — no FastAPI imports.

All path resolution for stored photos goes through this module.
Downstream specs (e.g. 12-sam2-segmentation) must use resolve_photo_path,
not construct paths manually.
"""

from pathlib import Path

# Default storage root: backend/.tmp/photos/
_DEFAULT_BASE_DIR = Path(__file__).parent.parent.parent / ".tmp"


def store_photo(
    measurement_id: str,
    photo_id: str,
    file_bytes: bytes,
    ext: str,
    *,
    base_dir: Path | None = None,
) -> Path:
    """Write photo bytes to disk and return the stored path.

    Storage path: {base_dir}/photos/{measurement_id}/{photo_id}{ext}
    Creates parent directories if they do not exist.

    Args:
        measurement_id: Session ID owning this photo.
        photo_id: UUID4 assigned to this photo.
        file_bytes: Raw file content.
        ext: File extension including dot (e.g. '.jpg', '.png').
        base_dir: Override the default .tmp base directory (used in tests).

    Returns:
        Path where the file was stored.
    """
    resolved_base = base_dir if base_dir is not None else _DEFAULT_BASE_DIR
    photo_dir = resolved_base / "photos" / measurement_id
    photo_dir.mkdir(parents=True, exist_ok=True)
    path = photo_dir / f"{photo_id}{ext}"
    path.write_bytes(file_bytes)
    return path


def resolve_photo_path(
    measurement_id: str,
    photo_id: str,
    *,
    base_dir: Path | None = None,
) -> Path:
    """Return the Path for a stored photo.

    Uses glob to find the file by photo_id regardless of extension.
    Raises FileNotFoundError if no matching file exists.

    Args:
        measurement_id: Session ID owning this photo.
        photo_id: UUID4 of the photo to resolve.
        base_dir: Override the default .tmp base directory (used in tests).

    Returns:
        Path to the stored photo file.

    Raises:
        FileNotFoundError: If no photo with that ID exists in the session.
    """
    resolved_base = base_dir if base_dir is not None else _DEFAULT_BASE_DIR
    photo_dir = resolved_base / "photos" / measurement_id
    matches = list(photo_dir.glob(f"{photo_id}.*"))
    if not matches:
        raise FileNotFoundError(
            f"No photo found for measurement_id={measurement_id!r}, photo_id={photo_id!r}"
        )
    return matches[0]
