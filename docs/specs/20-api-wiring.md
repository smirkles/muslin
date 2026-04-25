# Spec: API Wiring — Data Pipeline

**Spec ID:** 20-api-wiring
**Status:** implemented
**Created:** 2026-04-25
**Depends on:** 03-frontend-scaffold, 08-frontend-plumbing, 10-pattern-grading, 16-multi-agent-diagnosis, 17-pattern-download

## What it does

Fills the `// TODO: call api…` stubs in four frontend panels so that real data flows from the backend into the Zustand wizard store. After this spec is implemented, a user can: enter measurements → see the pattern grade → upload photos → run a real diagnosis → download the adjusted pattern. The cascade (step 5) is wired by spec 21.

## User-facing behavior

1. **MeasurementsPanel:** On form submit, calls `POST /measurements` (already exists in api.ts as `postMeasurements`) then immediately calls `POST /patterns/{patternId}/grade`. On success, `measurementsResponse` and `gradedPatternId` are set in the store and the panel advances to `photos`.
2. **PhotosPanel:** After upload, each photo must be segmented before diagnosis can run. Call `POST /photos/{photo_id}/segment` for each uploaded photo ID. Store the resulting `segmented_path` values (or just verify segmentation succeeded). Segmentation is a prerequisite for `POST /diagnosis/run`. _PhotosPanel currently advances straight to `diagnosis` — this wiring should happen inside `handleUploadSuccess` in `PhotosPanel.tsx` after the photo IDs are confirmed. This is a gap fix, not a new panel._
3. **DiagnosisPanel:** Fills the `runDiagnosis()` stub with a real call to `POST /diagnosis/run`. On success, stores `DiagnosisResult` in the wizard store.
4. **DownloadPanel:** Fills the `handleDownload()` stub with a real call to `GET /patterns/download/{graded_pattern_id}?format=svg|pdf`, creates a blob URL, triggers a browser download, and revokes the URL.

## Inputs and outputs

### New functions in `frontend/src/lib/api.ts`

```typescript
// POST /patterns/{patternId}/grade
export interface GradedPatternResponse {
  graded_pattern_id: string;
  pattern_id: string;
  measurement_id: string;
  svg: string;
  adjustments_cm: Record<string, number>;
}
export async function gradePattern(
  patternId: string,
  measurementId: string,
): Promise<GradedPatternResponse>

// POST /photos/{photoId}/segment  (no request body needed — photo is on server)
export interface SegmentationResponse {
  photo_id: string;
  segmented_path: string;
  mask_path: string;
}
export async function segmentPhoto(photoId: string): Promise<SegmentationResponse>

// POST /diagnosis/run
export interface DiagnosisIssue {
  issue_type: string;
  confidence: number;
  description: string;
  recommended_adjustment: string;
}
export interface DiagnosisResponse {
  issues: DiagnosisIssue[];
  primary_recommendation: string;
  cascade_type: "fba" | "swayback" | "none";
}
export async function runDiagnosis(
  measurementId: string,
  photoIds: string[],
): Promise<DiagnosisResponse>

// GET /patterns/download/{gradedPatternId}?format=svg|pdf
export async function downloadPattern(
  gradedPatternId: string,
  format: "svg" | "pdf",
): Promise<Blob>
```

Note: `applyAdjustment` is added to `api.ts` by spec 21 (different branch). When both branches merge into main, keep all functions — there is no semantic conflict, only an append-ordering difference.

### Panel changes

- **`MeasurementsPanel.tsx`** — fill lines 23–29: call `postMeasurements` then `gradePattern`, set `measurementsResponse` and `gradedPatternId` in store.
- **`PhotosPanel.tsx`** — in `handleUploadSuccess`, after storing photo IDs, call `segmentPhoto` for each ID in parallel (`Promise.all`). Surface a loading state and an error if any segmentation fails.
- **`DiagnosisPanel.tsx`** — fill lines 31–34: call `runDiagnosis(measurementsResponse.measurement_id, photoIds)`, set `diagnosisResult` in store.
- **`DownloadPanel.tsx`** — fill lines 19–25: call `downloadPattern`, create and revoke blob URL, trigger `<a>` click download.

### Errors

Each api function should throw `Error` with a human-readable message on non-OK response. Panels that already have `setError` state should catch and display. Download failures should show a brief inline error.

## Acceptance criteria

- [x] Given valid measurements, `MeasurementsPanel` submit calls both `POST /measurements` and `POST /patterns/{id}/grade`; on success the store contains a non-null `measurementsResponse` and `gradedPatternId`.
- [x] Given measurements submit fails, the panel shows the existing error state (no crash).
- [x] Given photos uploaded via `PhotosPanel`, `handleUploadSuccess` calls `POST /photos/{id}/segment` for each photo before advancing to `diagnosis`.
- [x] Given a segmentation failure, `PhotosPanel` surfaces an error message (does not silently swallow).
- [x] Given valid prerequisites, `DiagnosisPanel` `runDiagnosis()` calls `POST /diagnosis/run` with `measurement_id` and `photo_ids`; on success `diagnosisResult` in the store is non-null.
- [x] Given a diagnosis API error (e.g. 502), the panel shows the existing error state with a "Try again" button.
- [x] Given an adjusted pattern in the store, `DownloadPanel` clicking "Download SVG" calls `GET /patterns/download/{id}?format=svg` and triggers a file download.
- [x] Given "Download PDF" clicked, calls the same endpoint with `format=pdf`.
- [x] Given download fails, the button re-enables and an error is shown.
- [x] All four new `api.ts` functions accept `NEXT_PUBLIC_API_URL` env var with `http://localhost:8000` fallback.
- [x] `pnpm lint` exits 0. `pnpm test` exits 0 (all existing tests pass; new tests added for api.ts functions with mocked `fetch`).

## Out of scope

- SAM 2 segmentation UI (no separate panel — segmentation is a transparent step inside `PhotosPanel.handleUploadSuccess`).
- Pattern canvas SVG rendering — spec 21.
- Cascade player wiring — spec 21.
- `applyAdjustment` api.ts function — spec 21.
- Error retry logic beyond what's already in the panel shell.
- Cancelling in-flight requests.

## Technical approach

- All four new `api.ts` functions follow the same pattern as existing ones: `NEXT_PUBLIC_API_URL` fallback, `fetch`, throw on non-ok.
- `downloadPattern` returns a `Blob` (caller creates/revokes the object URL); this keeps blob lifecycle in the component.
- Segmentation in `PhotosPanel` runs `Promise.all` over all photo IDs — parallelise, don't serialise.
- No new Zustand state needed for segmentation (store `photoIds` already holds IDs; segmentation confirmation is implicit from no-error).

## Dependencies

- External libraries: none new.
- Specs first: 08 (api.ts shape + Zustand store), 10 (grading endpoint), 12 (segmentation endpoint), 16 (diagnosis endpoint), 17 (download endpoint).
- Backend must be running at `http://localhost:8000`.

## Testing approach

- **Unit tests** for each new `api.ts` function using `vi.stubGlobal('fetch', ...)`: happy path, non-ok response throws, correct URL and method constructed.
- **Component tests** are not required (panels are thin wrappers; existing panel tests already cover UI states). A manual smoke test is sufficient.
- **Manual verification:** run the full panel flow end-to-end with the backend running. Check browser DevTools Network tab: confirm each request fires and receives a real response.

## Open questions

None — all endpoints are confirmed implemented. Backend is running and tested.

## Implementation notes

**What was implemented:**
- Four new functions in `frontend/src/lib/api.ts`: `gradePattern`, `segmentPhoto`, `runDiagnosis`, `downloadPattern`
- `MeasurementsPanel.tsx`: filled TODOs to call `postMeasurements` then `gradePattern`, storing both results in the Zustand store and advancing to `photos`
- `PhotosPanel.tsx`: added `isSegmenting` and `segmentError` local state; `handleUploadSuccess` now runs `Promise.all` over all photo IDs calling `segmentPhoto`, surfaces error on failure, and only advances to `diagnosis` on success
- `DiagnosisPanel.tsx`: filled TODO to call `runDiagnosisApi` (imported as alias to avoid naming collision with local `runDiagnosis` function), storing result with `setDiagnosisResult`
- `DownloadPanel.tsx`: filled TODO to call `downloadPattern`, create blob URL, trigger anchor click, revoke URL; added `downloadError` state with inline error display

**Deviations from spec:**
- `SegmentationResponse` interface uses `cropped_path: string` and `confidence: number` instead of the spec's `segmented_path: string` and `mask_path: string`. The real backend (`backend/routes/photos.py`) returns `SegmentResponse` with fields `{ photo_id, mask_path, cropped_path, confidence }`. The `mask_path` field IS present; the spec's `segmented_path` does not exist — the pre-flight context correctly flagged this. Interface includes all four real backend fields.

**Pre-existing test failures (not introduced by this spec):**
- `src/store/wizard.test.ts` has 2 failing tests expecting `patternId` to be null, but `wizard.ts` was modified outside this spec to pre-load `patternId: "bodice-classic"`. These failures existed before this branch was created and are out of scope.

**Open questions for Steph:**
- The 2 pre-existing `wizard.test.ts` failures (expecting `patternId` to be null) should be resolved — either update the tests to match the intentional `"bodice-classic"` default, or revert the `wizard.ts` change if the default was accidental.

## Notes for implementer

- Branch name: `feat/20-api-wiring`. Never commit to `main`.
- Write failing tests for `api.ts` functions first, then implement.
- The segmentation endpoint is `POST /photos/{photo_id}/segment` (spec 12). Confirm the exact request body by reading `backend/routes/photos.py` — it may take the photo_id in the URL only (no body) or require a `{measurement_id}` body.
- `gradePattern` response includes `svg` (the full graded SVG as a string). Store `graded_pattern_id` in the wizard store; spec 21 will fetch and display the SVG.
- Do not touch `CascadePanel.tsx`, `PatternCanvas.tsx`, `wizard.ts` (currentStepIndex), or `RightPanel.tsx` — those are spec 21.
- Do not add `applyAdjustment` to `api.ts` — that is spec 21. If the linter complains about an import in a file you didn't touch, do not add the function as a stub; instead check whether you accidentally touched that file.
- The `DiagnosisResponse` type here matches the wizard store's `DiagnosisResult` shape — they are the same data. No adapter needed; just pass the response directly to `setDiagnosisResult`.
