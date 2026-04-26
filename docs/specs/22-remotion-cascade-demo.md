# Spec: Remotion Cascade Demo Composition

**Spec ID:** 22-remotion-cascade-demo
**Status:** ready-for-implementation
**Created:** 2026-04-26
**Depends on:** 13-cascade-animation-engine (for `CascadeScript` type and schema)

## What it does

A self-contained Remotion project (`remotion/`) that renders the cascade animation as a polished MP4 clip — the centrepiece of the Day 7 demo video. It consumes a hardcoded sample `CascadeScript` (3 FBA steps) and a simplified bodice SVG, animates each pattern transform using Remotion's `spring()` primitive, and displays the narration text as timed captions alongside. The output is a deterministic, re-renderable 20-second clip at 1080×1080 that can drop directly into the final demo video. No live app required, no screen recording, no browser chrome.

## User-facing behavior

Running `npx remotion render` from `remotion/` produces `out/cascade-demo.mp4`. Running `npx remotion studio` opens a preview at localhost where every frame is scrub-able. Re-running render after any code or data change produces a fresh, identical clip.

The clip itself:
1. Starts with the bodice front pattern piece on screen, at rest.
2. Step 1 animates: a slash line draws itself across the bust, pieces spread apart, narration appears below: *"First, we slash from the bust point to the side seam…"*
3. Step 2 animates: the new bust dart rotates into position, narration updates.
4. Step 3 animates: side seams translate to close, narration updates: *"Finally, we true the side seams."*
5. A brief hold on the finished adjusted pattern, then fade to black.

## Inputs and outputs

### Inputs

- `SAMPLE_CASCADE_SCRIPT: CascadeScript` — hardcoded in `remotion/src/data/sampleScript.ts`, satisfying the existing Zod schema from `13-cascade-animation-engine`. Three steps: one `translate` (spread), one `rotate` (dart), one `translate` (true seam).
- `BODICE_SVG` — a simplified bodice front SVG (`remotion/public/bodice-front.svg`) with named element IDs matching those referenced in `SAMPLE_CASCADE_SCRIPT`. Does not need to be the real production pattern — a clean geometric approximation is fine.

### Outputs

- `remotion/out/cascade-demo.mp4` — 1080×1080, 30fps, ~20s, H.264.
- The Remotion Studio preview (dev only).

### Errors

- If a step's `elementId` is not found in the SVG at render time, the render should throw with a clear message rather than silently skip the animation. Use `delayRender` / `continueRender` pattern if async loading is needed.

## Acceptance criteria

- [ ] `npx remotion render` from `remotion/` exits 0 and produces `out/cascade-demo.mp4`.
- [ ] The MP4 is exactly 600 frames (20s at 30fps).
- [ ] Frame 0 shows the bodice pattern at rest with no narration visible.
- [ ] Each cascade step's transform animates using `spring()` — no instant jumps between states.
- [ ] Narration text for each step appears at the start of that step's `<Sequence>` and is replaced (not appended) when the next step begins.
- [ ] The background is white or a light neutral — no default Remotion blue.
- [ ] The composition uses the `CascadeScript` type imported from `../frontend/src/lib/cascade_player/CascadeScript` (not a local copy) — single source of truth.
- [ ] `npx remotion studio` opens without errors and the composition appears in the sidebar.
- [ ] No TypeScript errors (`tsc --noEmit` exits 0 from `remotion/`).

## Out of scope

- Animating SVG path morphing (drawing the slash line as a stroke) — translate/rotate/scale only for V1.
- Audio voiceover in this composition — that is assembled in the final full demo video.
- Any composition other than the cascade scene — title cards, UI mockup scenes, etc. are separate work.
- Rendering to anything other than local MP4 (no Remotion Lambda for this spec).
- Using the real production bodice SVG — a simplified stand-in is fine.
- Playback controls — this is a render target, not an interactive player.

## Technical approach

### Project structure

```
remotion/
  package.json          # remotion, @remotion/captions, typescript
  tsconfig.json         # extends ../frontend/tsconfig, paths alias for cascade_player
  remotion.config.ts
  src/
    index.ts            # registerRoot
    Root.tsx            # <Composition id="CascadeDemo" ...>
    CascadeDemo.tsx     # top-level composition component
    StepSequence.tsx    # renders one CascadeStep as a <Sequence>
    NarrationCaption.tsx # renders narration text with fade-in
    data/
      sampleScript.ts   # SAMPLE_CASCADE_SCRIPT constant
  public/
    bodice-front.svg
```

### Animation model

Each step occupies `Math.round(step.durationMs / 1000 * fps)` frames. Steps are laid out sequentially with `<Series>` or manually computed `from` offsets. Within each step a `spring({ frame, fps })` drives the transform value, mapped via `interpolate()` to the target dx/dy/angle/scale. A short hold (15 frames) follows each step before the next begins.

### SVG rendering

The bodice SVG is loaded with `<Img>` or inlined as a React component via SVGR. Elements to be animated are identified by id and have `style={{ transform }}` applied, with `transformBox: "fill-box"` and `transformOrigin: "center center"` so rotations pivot correctly.

### Captions

`NarrationCaption` renders the current step's `narration` string with an `opacity` driven by `interpolate(frame, [0, 8], [0, 1])` for a quick fade-in at the start of each `<Sequence>`.

### TypeScript path alias

`tsconfig.json` in `remotion/` includes a path alias `"@cascade/*": ["../frontend/src/lib/cascade_player/*"]` so the import of `CascadeScript` doesn't need a brittle relative path.

## Dependencies

- External libraries: `remotion`, `@remotion/captions`, `typescript` (all in `remotion/package.json`)
- `@remotion/paths` not required for V1 (no path morphing in scope)
- Other specs: `13-cascade-animation-engine` must be implemented (provides `CascadeScript` type) — it is.
- No backend dependencies.

## Testing approach

- **Manual verification:** `npx remotion studio` → scrub through all 600 frames, confirm each step animates, confirm narration updates correctly.
- **Render test:** `npx remotion render` produces a non-zero-byte MP4 — can be wired into CI as a smoke test.
- No Vitest unit tests for this spec — the Remotion preview is the verification mechanism. The `CascadeScript` type is already tested in spec 13.

## Open questions

None — ready for implementation.

## Notes for implementer

- The `remotion/` directory is a sibling of `frontend/` and `backend/` — not nested inside either.
- The `CascadeScript` type lives in `frontend/src/lib/cascade_player/CascadeScript.ts`. Import it via the path alias rather than copying. This means any schema changes in spec 13 automatically apply here.
- The sample script's `elementId` values must match actual `id` attributes in `bodice-front.svg`. Design the SVG and script together.
- Keep the sample script to 3 steps. Enough to show the FBA story; short enough that the total composition fits in ~20s.
- `"use client"` directives from the cascade_player source do NOT apply in a Remotion context — Remotion is not Next.js. The import of `CascadeScript.ts` may trigger a lint warning because of the `"use client"` at the top of that file; suppress with a comment if needed or strip it in the path-aliased import.
- At 30fps, `durationMs: 1500` = 45 frames. Tune spring `damping` and `mass` until transforms look like they settle cleanly within the allocated frames — `measureSpring()` is useful here.
