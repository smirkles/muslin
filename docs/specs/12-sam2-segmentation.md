# Spec: SAM 2 Muslin Segmentation

**Spec ID:** 12-sam2-segmentation
**Status:** ready-for-implementation
**Created:** 2026-04-25
**Depends on:** 11-photo-upload (photo temp storage convention)

## What it does

Given a photo of a person wearing a muslin garment, segments the muslin from the background using SAM 2 via the Replicate API. Returns a binary mask (PNG) and a cropped version of the photo showing only the garment region. This is the first step in the fit diagnosis pipeline — without a clean mask the diagnosis agents cannot reliably read the muslin. All segmentation logic lives in `backend/lib/segmentation/` with no FastAPI imports.

## User-facing behavior

No direct UI. The calling surface is an HTTP endpoint:

1. A caller sends `POST /photos/{photo_id}/segment`.
2. The backend loads the photo from temp storage, calls Replicate's SAM 2 model with a centre-point foreground prompt, and writes the mask + cropped image to temp storage alongside the original.
3. Returns `{photo_id, mask_path, cropped_path, confidence}`.
4. If Replicate is unavailable or the photo cannot be found, a clear HTTP error is returned.

## Inputs and outputs

### Library interface — `backend/lib/segmentation/`

```python
# backend/lib/segmentation/segmenter.py
class Segmenter(Protocol):
    def segment(self, photo_path: Path, point_prompt: tuple[float, float] | None = None) -> SegmentationResult: ...

@dataclass(frozen=True)
class SegmentationResult:
    photo_id: str
    mask_path: Path        # binary PNG mask, same resolution as input
    cropped_path: Path     # input photo with background removed (RGBA PNG)
    confidence: float      # 0.0–1.0, from Replicate response
```

- `backend/lib/segmentation/replicate_segmenter.py` — concrete implementation; reads `REPLICATE_API_TOKEN` at `segment()` call time; raises `ConfigError` if missing.
- Point prompt defaults to `(0.5, 0.5)` (normalised centre of image) when not supplied.

### HTTP endpoint — `POST /photos/{photo_id}/segment`

#### Path param
- `photo_id: str` — must correspond to a photo stored by the photo upload feature.

#### Request body
- `point_prompt: [float, float] | null` — optional normalised `[x, y]` foreground point. Defaults to image centre.

#### Response body (200)
- `photo_id: str`
- `mask_path: str` — server-relative path to mask PNG
- `cropped_path: str` — server-relative path to RGBA crop PNG
- `confidence: float`

#### Errors
- **404** — `photo_id` not found in temp storage → `{"detail": "Photo not found"}`.
- **500** — `REPLICATE_API_TOKEN` missing → `{"detail": "REPLICATE_API_TOKEN not configured"}`.
- **502** — Replicate SDK raised an error → `{"detail": "Segmentation service error"}`. Full exception logged server-side; not leaked to client.
- **422** — malformed request body (FastAPI validation).

### Env vars

```bash
# backend/.env.example (add to existing)
REPLICATE_API_TOKEN=          # required for segmentation; leave blank in .env.example
REPLICATE_SAM2_MODEL=meta/sam-2   # optional override; default hardcoded in segmenter
```

## Acceptance criteria

- [ ] Given a valid photo path and no point prompt, when `ReplicateSegmenter().segment(photo_path)` is called with the Replicate client mocked, then `segment()` calls the client with model `meta/sam-2`, a single foreground point at `[0.5, 0.5]`, and the image encoded as base64.
- [ ] Given a valid photo path and an explicit `point_prompt=(0.3, 0.7)`, when `segment()` is called, then the Replicate call uses `[0.3, 0.7]` as the point coordinates.
- [ ] Given a mocked Replicate response with mask data and `iou_score=0.92`, when `segment()` returns, then `SegmentationResult.confidence == 0.92` and `mask_path` and `cropped_path` exist on disk.
- [ ] Given `REPLICATE_API_TOKEN` is unset, when `segment()` is called, then `ConfigError` is raised with a message mentioning the env var name.
- [ ] Given the Replicate client raises an exception, when `segment()` is called, then the exception propagates to the caller (not swallowed).
- [ ] Given a valid `photo_id` with the Replicate client patched, when `POST /photos/{photo_id}/segment` is called, then the response is 200 with `photo_id`, `mask_path`, `cropped_path`, and `confidence` fields.
- [ ] Given an unknown `photo_id`, when `POST /photos/{photo_id}/segment` is called, then the response is 404 with `detail="Photo not found"`.
- [ ] Given `REPLICATE_API_TOKEN` is unset, when `POST /photos/{photo_id}/segment` is called, then the response is 500 with `detail="REPLICATE_API_TOKEN not configured"`.
- [ ] Given the Replicate client raises an exception, when `POST /photos/{photo_id}/segment` is called, then the response is 502 with `detail="Segmentation service error"` and the original exception message is not in the response body.
- [ ] `backend/lib/segmentation/` contains no imports from `fastapi` or any HTTP framework (enforced by import-hygiene test).
- [ ] A live smoke test marked `@pytest.mark.integration` exists that, when `REPLICATE_API_TOKEN` is set, calls Replicate with a real test image and asserts a non-empty mask is returned. Skipped otherwise.
- [ ] `uv run pytest` passes; `uv run ruff check . && uv run black --check .` exit 0.

## Out of scope

- Multi-mask selection (SAM 2 can return multiple masks; use the highest-confidence one).
- Video segmentation (image only).
- Local SAM 2 inference — Replicate only.
- User-facing point-selection UI (point defaults to image centre; UI can be added later).
- Permanent storage — temp files only, session-scoped.
- Segmentation of multiple people in one photo.

## Technical approach

- `backend/lib/segmentation/segmenter.py` — `Segmenter` Protocol + `SegmentationResult` + `ConfigError`.
- `backend/lib/segmentation/replicate_segmenter.py` — calls `replicate.run(model, input={image, points})`. Writes mask PNG and RGBA crop to the same temp directory as the source photo (from spec 11's storage convention). Returns `SegmentationResult`.
- `backend/routes/photos.py` — gains `POST /photos/{photo_id}/segment`. Thin: resolves photo path from session store, constructs `ReplicateSegmenter()` via `get_segmenter()` factory (for test patching), calls `segment()`, maps exceptions to HTTP codes.
- Mask-to-RGBA crop: apply binary mask as alpha channel using `Pillow` (already likely in deps via pattern_ops).

## Dependencies

- External libraries needed: `replicate` (add to `backend/pyproject.toml`), `Pillow` (for mask application).
- Other specs that must be implemented first: `11-photo-upload` (defines temp storage convention and `photo_id` resolution).
- External services: Replicate API. Requires `REPLICATE_API_TOKEN` in `.env.local` for the live smoke test.

## Testing approach

- **Unit tests (mocked):** `backend/tests/test_sam2_segmenter.py` — cover `segment()` with Replicate client patched. Happy path, missing env var, Replicate exception, point prompt passthrough.
- **Route tests (mocked):** `backend/tests/test_routes_photos_segment.py` — cover 200 / 404 / 500 / 502 with `get_segmenter` patched.
- **Import-hygiene test:** assert `backend/lib/segmentation/` has no `fastapi` transitive imports.
- **Live smoke test (`@pytest.mark.integration`):** hits real Replicate API when `REPLICATE_API_TOKEN` is set. Uses a fixture image. Asserts non-empty mask PNG returned.

## Open questions

1. **Replicate model ID:** `meta/sam-2` (video variant) vs `meta/sam-2-image` (image-only). Recommended default: `meta/sam-2` with `REPLICATE_SAM2_MODEL` env var override so it can be changed without a code push. Verify with a smoke test before moving to `ready-for-implementation`.
2. **Photo path resolution:** spec 11's storage convention is TBD at time of writing. If spec 11 lands first, implementer should align on the `photo_id → path` helper rather than duplicating resolution logic.

## Notes for implementer

- Follow the exact same ConfigError / 500 hardcoding pattern from `backend/routes/dev.py` — hardcode the detail string in the route, log the verbose message.
- `get_segmenter()` factory in the route enables clean test patching (same pattern as `get_agent()` in spec 09).
- Temp storage should use the session-scoped directory from spec 11. If spec 11 is not yet implemented, stub with a configurable temp dir path.
- Write failing tests first per `CLAUDE.md` rule 5.
