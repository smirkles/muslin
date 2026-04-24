"""Photos route — POST /photos/upload.

Thin handler: validate all files, store all, return records.
All business logic lives in lib/photos/.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import BaseModel

from lib.measurements import get_measurements
from lib.photos.store import store_photo
from lib.photos.validate import (
    PhotoInvalidTypeError,
    PhotoTooLargeError,
    validate_photo,
)

router = APIRouter(tags=["photos"])

VALID_LABELS = {"front", "back", "side"}


class PhotoRecord(BaseModel):
    """A single uploaded photo record returned by the upload endpoint."""

    photo_id: str
    view_label: str
    filename: str


@router.post("/photos/upload", response_model=list[PhotoRecord])
async def upload_photos(
    measurement_id: Annotated[str, Form()],
    photos: Annotated[list[UploadFile], Form()] = None,  # type: ignore[assignment]
    view_labels: Annotated[list[str], Form()] = None,  # type: ignore[assignment]
) -> list[PhotoRecord]:
    """Accept 1–3 JPEG/PNG photos and store them in the session temp directory.

    Validates all files before writing any (all-or-nothing semantics).
    Returns a list of PhotoRecord objects on success.
    """
    # Normalise None defaults to empty list
    photos = photos or []
    view_labels = view_labels or []

    # --- File count validation ---
    if len(photos) == 0 or len(photos) > 3:
        raise HTTPException(status_code=400, detail="Upload 1–3 photos")

    # --- Label count validation ---
    if len(view_labels) != len(photos):
        raise HTTPException(status_code=400, detail="Each photo must have a view label")

    # --- Label value validation ---
    for label in view_labels:
        if label not in VALID_LABELS:
            raise HTTPException(
                status_code=400,
                detail="view_label must be one of: front, back, side",
            )

    # --- Measurement ID validation ---
    try:
        get_measurements(measurement_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Measurements not found") from exc

    # --- All-or-nothing: read and validate all bytes before writing anything ---
    file_data: list[tuple[bytes, str]] = []  # (bytes, filename) per file
    for upload in photos:
        content = await upload.read()
        filename = upload.filename or "photo"
        try:
            validate_photo(content, filename)
        except PhotoTooLargeError as exc:
            raise HTTPException(status_code=413, detail="Each photo must be under 10 MB") from exc
        except PhotoInvalidTypeError as exc:
            raise HTTPException(
                status_code=415, detail="Only JPEG and PNG files are accepted"
            ) from exc
        file_data.append((content, filename))

    # --- Store all files (all validation passed) ---
    records: list[PhotoRecord] = []
    for (content, filename), label in zip(file_data, view_labels, strict=True):
        photo_id = str(uuid.uuid4())
        ext = _get_extension(filename)
        store_photo(measurement_id, photo_id, content, ext)
        records.append(
            PhotoRecord(
                photo_id=photo_id,
                view_label=label,
                filename=filename,
            )
        )

    return records


def _get_extension(filename: str) -> str:
    """Return the lowercase extension including dot, or '.jpg' as fallback."""
    dot_pos = filename.rfind(".")
    if dot_pos == -1:
        return ".jpg"
    return filename[dot_pos:].lower()
