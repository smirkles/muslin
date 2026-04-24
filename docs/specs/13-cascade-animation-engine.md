# Spec: GSAP Cascade Animation Engine

**Spec ID:** 13-cascade-animation-engine
**Status:** ready-for-implementation
**Created:** 2026-04-25
**Depends on:** 03-frontend-scaffold, 08-frontend-plumbing

## What it does

A self-contained GSAP animation engine living in `frontend/src/lib/cascade_player/` that accepts a "cascade script" (a JSON structure describing a sequence of SVG transform steps with narration text) and plays them back one by one — animating SVG elements and displaying narration. It knows nothing about pattern fitting or sewing. It is the "hands" that executes what the backend cascade logic (specs 14+) decides. This isolation means the animation engine can be tested, iterated, and demoed independently of any Claude or geometry work.

## User-facing behavior

A `CascadePlayer` React component renders an SVG pattern inline and a narration panel below it. When the user presses Play:

1. The first step's SVG transform animates (GSAP tween) over `step.durationMs`.
2. The narration text for that step fades in below the SVG.
3. Steps play sequentially. When all steps are done, `onComplete` fires.
4. Controls: **Play/Pause**, **Step Forward**, **Step Back**.
5. Step Back during playback: pauses and seeks to the start of the previous step.
6. If a referenced SVG element is not found at runtime, an error banner appears instead of crashing.

## Inputs and outputs

### CascadeScript JSON schema

```ts
type TransformStep =
  | { type: "translate"; elementId: string; dx: number; dy: number }
  | { type: "rotate";    elementId: string; angleDeg: number; pivotX: number; pivotY: number }
  | { type: "scale";     elementId: string; sx: number; sy: number; originX: number; originY: number };

interface CascadeStep {
  id: string;           // unique within script, used as React key
  transform: TransformStep;
  narration: string;    // plain text, displayed below SVG
  durationMs: number;   // GSAP tween duration
}

interface CascadeScript {
  version: "1";
  steps: CascadeStep[];
}
```

All coordinates are in SVG user units. Transforms are absolute (not relative to previous steps).

### CascadePlayer component

```ts
interface CascadePlayerProps {
  script: CascadeScript;
  svgContent: string;       // raw SVG markup string
  onComplete?: () => void;  // fires after the last step's tween completes
}
```

Located at `frontend/src/lib/cascade_player/CascadePlayer.tsx`.

### useCascadeTimeline hook

Internal hook at `frontend/src/lib/cascade_player/useCascadeTimeline.ts` that manages the GSAP timeline. Not exported from the package.

## Acceptance criteria

### Schema validation

- [ ] Given a script with `version: "1"` and at least one valid step, when `parseCascadeScript(json)` is called, then it returns a typed `CascadeScript` without throwing.
- [ ] Given a script with an unknown transform type `"shear"`, when `parseCascadeScript` is called, then a `ScriptValidationError` is thrown.
- [ ] Given a script with `version: "2"`, when `parseCascadeScript` is called, then `ScriptValidationError` is thrown.
- [ ] Given a script with a step missing `narration`, when `parseCascadeScript` is called, then `ScriptValidationError` is thrown.

### Animation

- [ ] Given a 2-step script, when `CascadePlayer` mounts and Play is pressed, then GSAP `to()` is called once per step with the correct element id and transform values.
- [ ] Given a `translate` step with `{dx: 10, dy: 5}`, when the step plays, then GSAP is called with `x: 10, y: 5` targeting the element matching `elementId`.
- [ ] Given a `rotate` step, when the step plays, then GSAP is called with `rotation: angleDeg, transformOrigin: "pivotX pivotY"`.
- [ ] Given a `scale` step, when the step plays, then GSAP is called with `scaleX: sx, scaleY: sy, transformOrigin: "originX originY"`.
- [ ] Given a 3-step script, when playback completes, then `onComplete` is called exactly once.
- [ ] Given a 2-step script, when Step Forward is pressed on step 1, then GSAP seeks to step 2's start position.
- [ ] Given playback is on step 2, when Step Back is pressed, then playback pauses and seeks to step 1's start.
- [ ] Given playback is in progress, when Pause is pressed, then the GSAP timeline pauses.
- [ ] Given playback is paused, when Play is pressed, then the timeline resumes from the current position.

### Narration

- [ ] Given a step with `narration: "We are adding a dart here."`, when that step begins playing, then the narration text appears in the narration panel.
- [ ] Narration from a previous step is replaced (not appended) when the next step starts.

### Error handling

- [ ] Given a step referencing `elementId: "nonexistent-element"`, when playback reaches that step, then an error banner is shown and playback stops (no uncaught exception).

### Boundary enforcement

- [ ] `frontend/src/lib/cascade_player/` source files import only from `react`, `gsap`, and `zod`. No imports from outside the lib except these three. (Verified by a test that parses import statements.)
- [ ] Source files in `cascade_player/` contain none of the strings `fba`, `swayback`, `dart`, `bust`, `pattern` (case-insensitive). This enforces the domain-ignorance invariant.

### General

- [ ] `pnpm test` passes with GSAP mocked.
- [ ] `pnpm lint` exits 0.

## Out of scope

- Streaming narration (text appears word by word).
- Undo/redo of individual transforms (step-back is sufficient for V1).
- Exporting the animated result as video or GIF.
- Rendering the SVG to a canvas (SVG inline only).
- Any knowledge of sewing, pattern fitting, FBA, swayback, or dart manipulation.
- JSON Schema export for the cascade script format.
- Narration length capping (scroll if long).

## Technical approach

- `frontend/src/lib/cascade_player/CascadeScript.ts` — Zod schema + `parseCascadeScript` + `ScriptValidationError`.
- `frontend/src/lib/cascade_player/CascadePlayer.tsx` — `"use client"` React component. Renders SVG via `dangerouslySetInnerHTML`. Delegates timeline to `useCascadeTimeline`.
- `frontend/src/lib/cascade_player/useCascadeTimeline.ts` — `"use client"` hook. Creates a GSAP timeline on mount. Exposes `play`, `pause`, `stepForward`, `stepBack`. Fires `onComplete` via GSAP `onComplete` callback on the final tween.
- `frontend/src/lib/cascade_player/index.ts` — re-exports `CascadePlayer` and `CascadeScript` type only.

### GSAP mock for tests

```ts
// vitest setup or per-test:
vi.mock("gsap", () => ({
  default: {
    timeline: () => ({ to: vi.fn().mockReturnThis(), pause: vi.fn(), play: vi.fn(), seek: vi.fn() }),
    to: vi.fn(),
  },
}));
```

## Dependencies

- External libraries needed: `gsap` (add to `frontend/package.json`), `zod` (add if not already present).
- Other specs that must be implemented first: `03-frontend-scaffold` (Next.js app exists), `08-frontend-plumbing` (project build tooling).
- No backend dependencies — this is frontend only.

## Testing approach

- **Unit tests** in `frontend/src/lib/cascade_player/__tests__/`: schema validation (Zod), `CascadePlayer` renders SVG content, narration updates on step, GSAP called with correct args, `onComplete` fires, error banner on missing element. GSAP mocked throughout.
- **Boundary tests:** import-statement parser asserting no external deps beyond react/gsap/zod; string-search asserting no domain vocabulary.
- **Manual verification:** feed a hand-crafted 3-step translate script against the bodice SVG; confirm smooth animation and narration display in the browser.

## Open questions

1. **`scale` in pattern_ops:** spec 01 (pattern_ops) does not currently include a `scale_element` primitive. The cascade script schema includes `scale` for forward-compat; if spec 14 (swayback) doesn't emit scale steps, the `scale` branch won't be exercised in V1. Recommended: keep it in the schema, write the GSAP branch, but don't require a test fixture that exercises it until a cascade emits scale steps.
2. **`dangerouslySetInnerHTML` trust model:** acceptable for a hackathon prototype where SVG comes from the backend we control. Flag for production hardening post-demo.

## Notes for implementer

- The `cascade_player/` lib must remain domain-ignorant. If you find yourself writing `if step.type === "fba"`, stop — that logic belongs in the backend cascade spec.
- GSAP `to()` targets SVG elements by querying `document.getElementById(elementId)` on the inline SVG. Confirm the SVG has `id` attributes on all animated elements.
- `"use client"` is required on both `CascadePlayer.tsx` and `useCascadeTimeline.ts` (they use browser APIs and GSAP).
- Write failing tests first per `CLAUDE.md` rule 5.
