"""Photos route — POST /photos/upload and POST /photos/{photo_id}/segment.

Thin handler: validate all files, store all, return records.
All business logic lives in lib/photos/ and lib/segmentation/.
"""

import logging
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from lib.measurements import get_measurements
from lib.photos.store import lookup_photo_by_id, store_photo
from lib.photos.validate import (
    PhotoInvalidTypeError,
    PhotoTooLargeError,
    validate_photo,
)
from lib.segmentation.passthrough_segmenter import PassthroughSegmenter
from lib.segmentation.replicate_segmenter import ReplicateSegmenter
from lib.segmentation.segmenter import ConfigError, Segmenter

logger = logging.getLogger(__name__)
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


@router.get("/photos/{photo_id}/image")
def get_photo_image(photo_id: str) -> Response:
    """Serve raw image bytes for a previously uploaded photo."""
    try:
        photo_path = lookup_photo_by_id(photo_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Photo not found") from exc
    suffix = photo_path.suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"
    return Response(content=photo_path.read_bytes(), media_type=media_type)


def _get_extension(filename: str) -> str:
    """Return the lowercase extension including dot, or '.jpg' as fallback."""
    dot_pos = filename.rfind(".")
    if dot_pos == -1:
        return ".jpg"
    return filename[dot_pos:].lower()


# ---------------------------------------------------------------------------
# Segmentation models
# ---------------------------------------------------------------------------


class SegmentRequest(BaseModel):
    """Optional request body for POST /photos/{photo_id}/segment."""

    point_prompt: Annotated[list[float], Field(min_length=2, max_length=2)] | None = None


class SegmentResponse(BaseModel):
    """Response body for POST /photos/{photo_id}/segment."""

    photo_id: str
    mask_path: str
    cropped_path: str
    confidence: float


def get_segmenter() -> Segmenter:
    """Return the segmenter instance used by the segment endpoint.

    Uses ReplicateSegmenter when REPLICATE_API_TOKEN is configured,
    otherwise falls back to PassthroughSegmenter (copies original as crop).
    Extracted so tests can patch it cleanly.
    """
    if os.environ.get("REPLICATE_API_TOKEN"):
        return ReplicateSegmenter()
    logger.info("REPLICATE_API_TOKEN not set — using PassthroughSegmenter")
    return PassthroughSegmenter()


@router.post("/photos/{photo_id}/segment", response_model=SegmentResponse)
def segment_photo(
    photo_id: str,
    body: Annotated[SegmentRequest | None, Body()] = None,
) -> SegmentResponse:
    """Segment the muslin garment from a previously uploaded photo.

    Errors:
        404 — photo_id not found in temp storage.
        500 — REPLICATE_API_TOKEN is missing from the environment.
        502 — Replicate SDK raised an error.
    """
    try:
        photo_path = lookup_photo_by_id(photo_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Photo not found") from exc

    point: tuple[float, float] | None = None
    if body and body.point_prompt is not None:
        point = (body.point_prompt[0], body.point_prompt[1])

    segmenter = get_segmenter()
    try:
        result = segmenter.segment(photo_path, point_prompt=point)
    except ConfigError as exc:
        logger.warning("REPLICATE_API_TOKEN not configured: %s", exc)
        raise HTTPException(status_code=500, detail="REPLICATE_API_TOKEN not configured") from exc
    except Exception as exc:
        logger.exception("Replicate segmentation error for photo_id=%s: %s", photo_id, exc)
        raise HTTPException(status_code=502, detail="Segmentation service error") from exc

    return SegmentResponse(
        photo_id=result.photo_id,
        mask_path=str(result.mask_path),
        cropped_path=str(result.cropped_path),
        confidence=result.confidence,
    )
