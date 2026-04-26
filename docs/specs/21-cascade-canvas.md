# Spec: Cascade Canvas & Playback Wiring

**Spec ID:** 21-cascade-canvas
**Status:** implemented
**Created:** 2026-04-25
**Depends on:** 08-frontend-plumbing, 13-cascade-animation-engine, 15-fba-cascade, 14-swayback-cascade

## What it does

Wires the visual layer of the workspace: the pattern SVG renders in the canvas, the cascade adjustment is fetched and played step-by-step, and the step index is shared across the canvas, the side panel, and the right-panel context strip. After this spec, a user can see the graded pattern on screen, trigger an adjustment, watch each step's SVG update in the canvas, and step forward/back through the cascade narration.

## User-facing behavior

1. **PatternCanvas — pattern display:** When `gradedPatternId` is set in the store, fetch `GET /patterns/{graded_pattern_id}` (or use the SVG returned from grading — see Notes) and render it inline in the canvas. Until then, show the existing "Pattern loads here" placeholder.
2. **CascadePanel — load cascade:** On open, if `diagnosisResult` is set and `cascadeScript` is not, call `POST /cascades/apply-adjustment` with `{pattern_id, adjustment_type, amount_cm}`. Default `amount_cm`: 2.0 for FBA, 1.2 for swayback. Store the result as `cascadeScript` in the wizard store.
3. **PatternCanvas — step SVG display:** When `cascadeScript` is set, render `cascadeScript.steps[currentStepIndex].svg` inline in the canvas (replacing the static pattern). SVG is pre-rendered by the backend — no GSAP transform animation needed.
4. **CascadePanel — playback controls:** Prev/Next buttons and the step dots update `currentStepIndex` in the store. The Play button auto-advances through steps at a fixed 2-second interval. Pause stops auto-advance.
5. **CascadePanel — before/after thumbnails:** Show `cascadeScript.steps[0].svg` (before) and `cascadeScript.steps[last].svg` (after) as small inline SVG previews.
6. **RightPanel — CascadeContext:** The cascade context strip reads `currentStepIndex` from the store and shows the active step's narration and a correctly-driven progress bar.
7. **CascadeProgressBar (in PatternCanvas):** Highlights the dot for `currentStepIndex`.

## Inputs and outputs

### New function in `frontend/src/lib/api.ts`

```typescript
// POST /cascades/apply-adjustment
export interface CascadeStepApiResponse {
  step_number: number;
  narration: string;
  svg: string;
}
export interface CascadeScriptApiResponse {
  adjustment_type: string;
  pattern_id: string;
  amount_cm: number;
  steps: CascadeStepApiResponse[];
  seam_adjustments: Record<string, number>;
}
export async function applyAdjustment(
  patternId: string,
  adjustmentType: string,
  amountCm: number,
): Promise<CascadeScriptApiResponse>
```

Note: spec 20 (different branch) adds `gradePattern`, `runDiagnosis`, `downloadPattern` to `api.ts`. When both branches merge, keep all functions — no semantic conflict, only an append-ordering difference in the file.

### Zustand store additions — `frontend/src/store/wizard.ts`

Add `currentStepIndex: number` (initial value `0`) and `setCurrentStepIndex: (i: number) => void` to `WizardState`. Reset `currentStepIndex` to `0` in `reset()`.

### `CascadeScriptApiResponse` vs `CascadeScript` (cascade_player)

**Important architectural note:** The existing `CascadePlayer` component (`frontend/src/lib/cascade_player/CascadePlayer.tsx`) expects a transform-based script (`{version: "1", steps: [{id, transform, narration, durationMs}]}`), which is **incompatible** with the backend's format (`{adjustment_type, steps: [{step_number, narration, svg}]}`). Do **not** use the `CascadePlayer` component for this integration. The backend pre-renders each step as a complete SVG string; just swap the SVG displayed in the canvas as `currentStepIndex` changes. No GSAP animation is needed — the visual change is the SVG itself changing.

The wizard store's `CascadeScript` type (already defined in `wizard.ts`) matches the backend format. Use it as-is.

## Acceptance criteria

- [x] Given `gradedPatternId` is set in the store, `PatternCanvas` renders the pattern SVG in the canvas (not the placeholder).
- [x] Given `gradedPatternId` is null, `PatternCanvas` shows the "Pattern loads here" placeholder.
- [x] Given `diagnosisResult` is set and `cascadeScript` is null, opening `CascadePanel` triggers `loadCascade()` which calls `POST /cascades/apply-adjustment`.
- [x] Given `loadCascade()` succeeds, `cascadeScript` is set in the store and the cascade UI appears.
- [x] Given `loadCascade()` fails, the panel shows an error with a "Try again" button.
- [x] Given `cascadeScript` is set, `PatternCanvas` renders `cascadeScript.steps[currentStepIndex].svg` inline.
- [x] Given `currentStepIndex` is `0`, the PatternCanvas shows step 0's SVG; advancing to index 1 shows step 1's SVG without a page reload.
- [x] Given the cascade panel's Next button is clicked, `currentStepIndex` increments by 1 in the store; Prev decrements; both are clamped to `[0, steps.length - 1]`.
- [x] Given the Play button is clicked, `currentStepIndex` auto-advances every 2 seconds until the last step or Pause is clicked.
- [x] Given `cascadeScript` is set, `CascadePanel` before/after thumbnails show `steps[0].svg` and `steps[steps.length - 1].svg` as small inline SVGs.
- [x] Given `cascadeScript` is set and `currentStepIndex` is `i`, `RightPanel`'s `CascadeContext` shows `steps[i].narration` (not always step 0).
- [x] Given `currentStepIndex` is `i`, `CascadeProgressBar` highlights dot `i`.
- [x] `pnpm lint` exits 0. `pnpm test` exits 0 (all existing tests pass; new tests added as described below).

## Out of scope

- GSAP transform animation — the backend pre-renders each step as an SVG; swap the SVG, don't animate transforms.
- Using the existing `CascadePlayer` component — incompatible format (see Architectural Note above). Leave the component untouched.
- Zoom/pan controls on the canvas SVG.
- Auto-advancing the step for the user based on a timer that persists across panel navigation.
- MeasurementsPanel, DiagnosisPanel, DownloadPanel API wiring — spec 20.
- `gradePattern`, `runDiagnosis`, `downloadPattern` api.ts functions — spec 20.
- **spec 19 (Three.js body viewer) — ON HOLD.** The `BodyViewer` component is already embedded in `RightPanel.tsx` (lines 28–47). Do not touch it, modify it, fix it, or investigate it. A separate agent is actively investigating a bug in the body viewer. Leave that section of `RightPanel.tsx` exactly as it is.

## Technical approach

- **Pattern SVG rendering:** Fetch and render inline. Two options — pick whichever is simpler to implement:
  - Option A: `gradePattern` returns `svg` in the response (already in the store as part of `GradedPatternResponse` from spec 20). If `gradedPatternId` is set, read the SVG from that stored response instead of a second fetch. _Preferred if spec 20 stores the full GradedPatternResponse rather than just the ID._
  - Option B: `useEffect` in `PatternCanvas` fetches `GET /patterns/{graded_pattern_id}` (returns `PatternDetail` with `svg` field) when `gradedPatternId` changes. Add `fetchPattern(id): Promise<{svg: string}>` to `api.ts` if needed.
  - Render via `dangerouslySetInnerHTML={{ __html: svg }}` inside a sized `<div>`. This is safe here — SVGs come from the backend we control.
- **Step SVG display:** Same `dangerouslySetInnerHTML` approach. `CascadeCanvas` in `PatternCanvas.tsx` renders `cascadeScript.steps[currentStepIndex].svg`.
- **Play auto-advance:** `useInterval`-style `useEffect` with `setInterval` / `clearInterval` inside `CascadePanel`. Store play/pause state locally in `CascadePanel` (no need to hoist it to the wizard store).
- **currentStepIndex shared state:** Lives in the wizard store so PatternCanvas, CascadePanel, CascadeProgressBar, and RightPanel.CascadeContext can all read it without prop drilling.

## Dependencies

- External libraries: none new.
- Specs first: 08 (Zustand store base shape), 13 (CascadePlayer — understand its format mismatch), 14/15 (cascade backend, confirms pre-rendered SVG per step).
- Backend must be running at `http://localhost:8000`.

## Testing approach

- **Unit tests** for `applyAdjustment` in api.ts: happy path (correct URL, method, body), non-ok throws.
- **Unit test** for `wizard.ts`: `setCurrentStepIndex` updates the store; `reset()` zeroes `currentStepIndex`.
- **Component tests** are not required for the canvas or panel display — too tightly coupled to DOM SVG rendering to be worth the setup overhead for a hackathon.
- **Manual verification:** With backend running, go through the full flow to the cascade step; confirm SVG updates in the canvas as you step forward/back; confirm narration updates in the right panel and progress bar moves.

## Open questions

None — all endpoints confirmed implemented. SVG format per step confirmed in `backend/routes/cascades.py` (`CascadeStepResponse.svg: str`).

## Notes for implementer

- Branch name: `feat/21-cascade-canvas`. Never commit to `main`.
- Write failing tests first (api.ts + wizard store slice), then implement.
- The `cascadeScript` in the wizard store already has the correct shape (`CascadeScript` type with `steps: [{step_number, narration, svg}]`). The `applyAdjustment` response maps directly to it — no adapter needed.
- Do NOT touch `MeasurementsPanel.tsx`, `DiagnosisPanel.tsx`, `DownloadPanel.tsx`, or `PhotosPanel.tsx` — those are spec 20.
- Do NOT use or modify `frontend/src/lib/cascade_player/`. That component expects a transform-based script format the backend doesn't emit. Leave it intact for a future V2 upgrade.
- `CascadePanel.loadCascade()` needs `amount_cm`. Use `diagnosisResult.cascade_type === "fba" ? 2.0 : 1.2` as the default. These values are hardcoded for V1 — no UI to change them.
- The `POST /cascades/apply-adjustment` request body field is `adjustment_type` (not `cascade_type`). See `backend/routes/cascades.py` line 23.
- When both spec 20 and spec 21 branches are merged into main, `api.ts` will have been modified by both. The merge should be clean (both branches append distinct functions). If git reports a conflict in `api.ts`, resolution is: keep all functions from both branches.
- After merge: manually fill `CascadePanel.loadCascade()` if you left it as a stub, OR wire it as part of this spec (preferred — it's a short call to `applyAdjustment`).
- **Do not touch `BodyViewer.tsx` or the body viewer section of `RightPanel.tsx` (lines 17–48).** A bug investigation is in progress on another agent instance. Edit only the `CascadeContext` function and below in that file.

## Implementation notes

### What was implemented

- `frontend/src/lib/api.ts`: Added `PatternDetail` interface, `fetchPattern()` (GET /patterns/{id}), `CascadeStepApiResponse`, `CascadeScriptApiResponse` interfaces, and `applyAdjustment()` (POST /cascades/apply-adjustment).
- `frontend/src/store/wizard.ts`: Added `currentStepIndex: number` (init `0`) to `WizardState` and `initialState`, added `setCurrentStepIndex` action, included in `reset()`.
- `frontend/src/components/workspace/PatternCanvas.tsx`: `PatternDisplay` now fetches SVG via `fetchPattern(gradedPatternId)` with loading/error states and renders via `dangerouslySetInnerHTML`. `CascadeCanvas` reads `currentStepIndex` from store and renders the appropriate step SVG. `CascadeProgressBar` highlights dot at `currentStepIndex`.
- `frontend/src/components/panels/CascadePanel.tsx`: `loadCascade()` wired to call `applyAdjustment` with FBA=2.0/swayback=1.2 defaults; result stored via `setCascadeScript`. Local `currentStep`/`setCurrentStep` replaced with `currentStepIndex`/`setCurrentStepIndex` from wizard store. Before/after thumbnails use `dangerouslySetInnerHTML`. Play auto-advance uses `setInterval(2000)` reading fresh index via `useWizardStore.getState()` to avoid stale closure trap; stops and sets `isPlaying=false` when last step reached.
- `frontend/src/components/workspace/RightPanel.tsx`: `CascadeContext` now reads `currentStepIndex` from store, shows `steps[currentStepIndex].narration`, drives progress bar width via `((currentStepIndex + 1) / totalSteps) * 100`, shows "Step N of M".

### Deviations from spec

- `RightPanel.tsx` had already been modified by another agent (the `BodyViewer` import was changed from a direct import to a `next/dynamic` import). The `CascadeContext` function was edited as specified; lines 1–48 were left untouched.
- `api.ts` at branch creation had spec 20's functions already applied (`gradePattern`, `runDiagnosis`, `downloadPattern` were already present). New functions were appended cleanly.

### Open questions

None. All acceptance criteria satisfied.

### New ADRs

None required.
