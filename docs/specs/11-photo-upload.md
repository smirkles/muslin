# Spec: Photo Upload

**Spec ID:** 11-photo-upload
**Status:** implemented
**Created:** 2026-04-25
**Depends on:** 07-measurements-fba-fields, 08-frontend-plumbing

## What it does

Lets the user upload 1–3 photos of themselves wearing a muslin garment (front, back, side views). The Next.js frontend provides a drag-and-drop upload component with thumbnail previews and per-photo view-label selection. The FastAPI backend stores the files to a session-scoped temp directory and returns a list of photo IDs the downstream segmentation and diagnosis steps will use. No permanent storage — photos are ephemeral, tied to the `measurement_id` session.

## User-facing behavior

1. User sees a drop zone with "Upload your muslin photos" and a click-to-browse fallback.
2. User drags or selects 1–3 JPEG or PNG files.
3. Thumbnails appear immediately via `URL.createObjectURL` (client-side, no round-trip).
4. A view-label selector (`Front / Back / Side`) appears under each thumbnail.
5. User clicks "Upload" — files and labels are sent in a single multipart POST.
6. On success, the wizard advances and stores the returned photo IDs in app state.
7. On failure (file too large, wrong type, too many files), an inline error message appears under the offending file.

## Inputs and outputs

### Frontend component — `PhotoUpload`

Props:
- `measurementId: string` — required, used as the session key in the POST.
- `onSuccess: (photos: PhotoRecord[]) => void` — called on successful upload.

### HTTP endpoint — `POST /photos/upload`

Multipart form data:
- `measurement_id: string` — must match an existing session in the measurement store.
- `photos: File[]` — 1–3 files, each JPEG or PNG, each ≤ 10 MB.
- `view_labels: string[]` — parallel array of `"front"`, `"back"`, or `"side"`, one per file.

Response (200):
```json
[
  {"photo_id": "uuid", "view_label": "front", "filename": "front.jpg"},
  {"photo_id": "uuid", "view_label": "back",  "filename": "back.jpg"}
]
```

### Backend storage

Photos stored at `backend/.tmp/photos/{measurement_id}/{photo_id}{ext}`. The `.tmp/` directory is gitignored. `photo_id` is a UUID4 generated at upload time.

A helper `resolve_photo_path(measurement_id, photo_id) -> Path` in `backend/lib/photos/store.py` is the single source of truth for path resolution — downstream specs (12-sam2-segmentation) must use this helper, not construct paths manually.

### Errors

- **400** — zero files or more than 3 files → `{"detail": "Upload 1–3 photos"}`.
- **400** — mismatched `photos` / `view_labels` lengths → `{"detail": "Each photo must have a view label"}`.
- **400** — invalid view label (not `front`, `back`, `side`) → `{"detail": "view_label must be one of: front, back, side"}`.
- **404** — `measurement_id` not in session store → `{"detail": "Measurements not found"}`.
- **413** — any file > 10 MB → `{"detail": "Each photo must be under 10 MB"}`.
- **415** — file fails MIME check (extension + magic byte sniff) → `{"detail": "Only JPEG and PNG files are accepted"}`.
- **422** — malformed form data (FastAPI validation).

## Acceptance criteria

### Backend lib — `backend/lib/photos/`

- [ ] Given a valid JPEG file, when `validate_photo(file)` is called, then it returns without raising.
- [ ] Given a PNG file with a `.jpg` extension (mismatched magic bytes), when `validate_photo` is called, then `PhotoValidationError` is raised mentioning MIME mismatch.
- [ ] Given a file > 10 MB, when `validate_photo` is called, then `PhotoValidationError` is raised mentioning the size limit.
- [ ] Given a valid file, when `store_photo(measurement_id, photo_id, file_bytes, ext)` is called, then `resolve_photo_path(measurement_id, photo_id)` returns a path that exists on disk with matching bytes.
- [ ] `resolve_photo_path` raises `FileNotFoundError` for an unknown `photo_id`.
- [ ] `backend/lib/photos/` contains no `fastapi` imports (import-hygiene test).

### HTTP endpoint

- [ ] Given 2 valid files with matching view labels and a valid `measurement_id`, `POST /photos/upload` returns 200 with a list of 2 `PhotoRecord` objects, each with `photo_id`, `view_label`, and `filename`.
- [ ] Given 0 files, response is 400 with `detail="Upload 1–3 photos"`.
- [ ] Given 4 files, response is 400 with `detail="Upload 1–3 photos"`.
- [ ] Given mismatched `photos` and `view_labels` counts, response is 400.
- [ ] Given an invalid view label `"diagonal"`, response is 400.
- [ ] Given an unknown `measurement_id`, response is 404.
- [ ] Given a file > 10 MB, response is 413.
- [ ] Given a GIF file, response is 415.
- [ ] Validation is all-or-nothing: if any file is invalid, no files are written to disk and the response is an error.

### Frontend component

- [ ] Given 1 dropped JPEG file, a thumbnail renders immediately before the upload button is clicked.
- [ ] Given a dropped file > 10 MB, an inline error message appears and the file is not submitted.
- [ ] Given a successful upload response, `onSuccess` is called with the returned `PhotoRecord[]`.
- [ ] Given an API error response, an error message is displayed and the user can retry.
- [ ] The upload button is disabled until at least one file is selected and all selected files have a view label chosen.
- [ ] Uploading more than 3 files shows an inline error; only the first 3 are kept.

### General

- [ ] `uv run pytest` passes; `uv run ruff check . && uv run black --check .` exit 0.
- [ ] `pnpm test` passes.

## Out of scope

- Permanent storage or database records.
- `GET /photos/{photo_id}` endpoint (needed for annotation overlays, deferred to a future spec).
- EXIF rotation correction.
- Per-file upload progress bars (single batch POST).
- HEIC / WebP support.
- Mobile camera capture (`<input capture>`).
- Virus scanning.
- Cleanup of temp files (deferred — no cleanup in V1).

## Technical approach

- `backend/lib/photos/__init__.py`, `store.py`, `validate.py` — pure logic, no FastAPI imports.
- `backend/routes/photos.py` — new router at `/photos`. Thin handler: validate all files, store all, return records. Uses `python-multipart` (verify it is in `pyproject.toml`).
- `frontend/src/components/PhotoUpload.tsx` — drag-and-drop via HTML5 File API. Thumbnails via `URL.createObjectURL`. Submits with `postPhotos(measurementId, files, viewLabels)` from the API client (spec 08).
- `frontend/src/lib/api.ts` — add `postPhotos` function.
- Storage path: `backend/.tmp/photos/{measurement_id}/{photo_id}{ext}`. Create directories on first write. Add `backend/.tmp/` to `.gitignore`.

## Dependencies

- External libraries needed: `python-multipart` (verify in `pyproject.toml`), `Pillow` (magic-byte MIME sniff).
- Other specs that must be implemented first: `07-measurements-fba-fields` (session store for `measurement_id` validation), `08-frontend-plumbing` (API client).
- No new external services.

## Testing approach

- **Unit tests** in `backend/tests/test_photo_lib.py`: validate_photo happy path, wrong MIME, oversized, store round-trip, resolve_photo_path missing file, import-hygiene.
- **Route tests** in `backend/tests/test_routes_photos.py`: all error codes, happy path with mocked lib, all-or-nothing validation.
- **Frontend tests** in `frontend/src/components/__tests__/PhotoUpload.test.tsx`: thumbnail render, error display, onSuccess callback, disabled-until-ready button.
- **Manual verification:** drag 2 photos into the component; confirm thumbnails, labels, and upload succeed; check files land in `backend/.tmp/`.

## Open questions

1. **Cleanup policy:** temp files are never deleted in V1. If this causes disk issues during a long demo session, a simple `DELETE /photos/upload?measurement_id=X` can be added. No action needed before implementation.
2. **`python-multipart` version:** confirm it is already in `pyproject.toml` (FastAPI requires it for file uploads but may not pin it explicitly).

## Notes for implementer

- `resolve_photo_path` is the canonical path-resolution function. Spec 12 (SAM 2) will import it — do not let downstream specs reinvent path logic.
- All-or-nothing validation: validate every file before writing any. If one fails, return the error without touching disk.
- Magic-byte sniff: JPEG starts with `FF D8 FF`; PNG starts with `89 50 4E 47`. Read first 8 bytes only.
- Write failing tests first per `CLAUDE.md` rule 5.

## Implementation notes

### What was implemented

- `backend/lib/photos/__init__.py` — package stub
- `backend/lib/photos/validate.py` — `validate_photo(file_bytes, filename)` with `PhotoValidationError`, `PhotoTooLargeError`, `PhotoInvalidTypeError` exception hierarchy; magic-byte sniff without Pillow (raw bytes is sufficient)
- `backend/lib/photos/store.py` — `store_photo(measurement_id, photo_id, file_bytes, ext, *, base_dir)` and `resolve_photo_path(measurement_id, photo_id, *, base_dir)` using glob to find files by photo_id regardless of extension
- `backend/routes/photos.py` — thin route at `POST /photos/upload` with all-or-nothing validation
- `backend/main.py` — registered `photos_router`
- `.gitignore` — added `backend/.tmp/` entry
- `frontend/src/lib/api.ts` — added `PhotoRecord` interface and `postPhotos()` function
- `frontend/src/components/PhotoUpload.tsx` — drag-and-drop component with thumbnails, per-file view label selectors, client-side size validation, and error display

### Deviations from the spec

1. **Pillow not used for magic-byte sniff.** The spec listed Pillow as a dependency for MIME sniffing, but Pillow is overkill: reading 8 raw bytes and comparing against known magic byte sequences is simpler, faster, and has no extra dependency. Both `python-multipart` and `Pillow` were already in `pyproject.toml` anyway — Pillow was just not needed for this.

2. **`validate_photo` signature is `(file_bytes: bytes, filename: str)`.** The spec left the signature undefined. This is the natural shape given that `store_photo` also takes bytes, and it makes unit tests trivially simple (pass `bytes` literals directly).

3. **`store_photo` and `resolve_photo_path` accept a `base_dir` keyword argument.** This allows tests to redirect storage to `tmp_path` without patching globals. Not mentioned in the spec but doesn't change the public contract for downstream specs — they call these functions without `base_dir` and get the default `backend/.tmp/` path.

4. **Zero-file case returns 400 (not 422).** When no `photos` field is sent at all, FastAPI normally returns 422 for missing required fields. The route uses `photos = None` as the default (with `# type: ignore[assignment]`) and normalises `None` to `[]` before the count check, so the response is 400 with the spec-mandated detail.

5. **Frontend file input is visually hidden via inline style (not Tailwind `hidden`).** Using `className="hidden"` prevents `userEvent.upload` from working in tests because JSDOM treats `display: none` elements as not accepting uploads. Instead, `style={{ position: "absolute", width: 1, height: 1, opacity: 0, ... }}` hides it visually while keeping it accessible and testable.

### Open questions for Steph

- None. Both open questions in the spec are resolved (cleanup is deferred, python-multipart was confirmed present).

### New ADRs

None needed — choices are minor implementation details documented here.
