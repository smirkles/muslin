# Spec: FBA Cascade Engine

**Spec ID:** 15-fba-cascade
**Status:** implemented
**Created:** 2026-04-24
**Depends on:** 01-pattern-svg-library, 04-measurements-endpoint, 06-pattern-registry

## What it does

Applies a Full Bust Adjustment (FBA) to the bodice pattern. Given a pattern and an FBA amount in cm, it produces: (a) an adjusted SVG pattern where the front side panel has been spread outward and a bust dart added, and (b) a cascade script — an ordered list of steps with narration and the SVG state at each step. The cascade script is what the frontend player animates.

FBA is the single most common fitting alteration for home sewers with a full bust. The standard technique: draw a vertical slash from the bust column down to the hem, open the slash by the FBA amount, and take in the resulting extra width as a new bust dart at the side seam.

## User-facing behavior

No direct user interaction. Called by the `/apply-adjustment` endpoint. The endpoint returns the cascade script JSON, which the frontend plays back as an animated explanation.

## Inputs and outputs

### `apply_fba` function

```python
def apply_fba(
    pattern: Pattern,
    fba_amount_cm: float,
    pattern_id: str = "bodice-v1",
) -> CascadeResult
```

- `pattern` — a `Pattern` loaded from the bodice-v1 SVG. Must contain elements:
  `front-cf-panel`, `front-side-panel`, `front-waist-dart`
- `fba_amount_cm` — the FBA amount in centimetres. Valid range: `0.5 ≤ amount ≤ 6.0`.
- `pattern_id` — string identifier for the pattern; included in the cascade script output.

### `CascadeResult` (new dataclass in `backend/lib/cascade/types.py`)

```python
@dataclass
class CascadeStep:
    step_number: int   # 1-indexed
    narration: str     # plain-English explanation text
    svg: str           # full SVG string for this visual state

@dataclass
class CascadeScript:
    adjustment_type: str   # "fba" or "swayback"
    pattern_id: str
    amount_cm: float
    steps: list[CascadeStep]

@dataclass
class CascadeResult:
    adjusted_pattern: Pattern
    cascade_script: CascadeScript
```

These types are **the contract between backend cascade engines and the frontend player**. The frontend (spec 11) imports the JSON serialisation of `CascadeScript`. Do not change the field names without updating both sides.

### `POST /apply-adjustment` endpoint

Request body:
```json
{
  "pattern_id": "bodice-v1",
  "adjustment_type": "fba",
  "amount_cm": 2.5
}
```

Response body (HTTP 200):
```json
{
  "cascade_script": {
    "adjustment_type": "fba",
    "pattern_id": "bodice-v1",
    "amount_cm": 2.5,
    "steps": [
      { "step_number": 1, "narration": "...", "svg": "<?xml..." },
      { "step_number": 2, "narration": "...", "svg": "<?xml..." },
      { "step_number": 3, "narration": "...", "svg": "<?xml..." },
      { "step_number": 4, "narration": "...", "svg": "<?xml..." }
    ]
  }
}
```

### Errors

- `amount_cm` outside `[0.5, 6.0]` → HTTP 422 with `{"detail": "fba_amount_cm must be between 0.5 and 6.0"}`
- `pattern_id` not in registry → HTTP 404
- Pattern is missing required elements → HTTP 500 with detail naming the missing element

## Cascade steps for FBA

The `apply_fba` function produces **exactly 4 steps**:

| Step | What changes | Narration (suggested; implementer may refine) |
|------|-------------|------|
| 1 | Base pattern, no changes | "Starting with your size-graded bodice block." |
| 2 | Slash line added at bust column (x=115, from y=6 to y=360) | "We draw a slash line from the bust point to the hem — this is where we'll open the pattern." |
| 3 | `front-side-panel` translated right by `fba_px`; slash line present | "Opening the slash by {amount_cm} cm creates room for your full bust." |
| 4 | Bust dart added; slash line still visible | "A new bust dart at the side seam takes in the extra fabric. Your adjusted front bodice is ready." |

`fba_px` conversion: `fba_amount_cm × 10 × 0.5` (1 cm = 10 mm; 1 mm = 0.5 SVG units at bodice-v1 scale).

## Algorithm

```
fba_px = fba_amount_cm * 10 * 0.5

step1: render base pattern → step 1 SVG

step2:
  p = slash_line(pattern, from_pt=(115, 6), to_pt=(115, 360), slash_id="fba-slash-1")
  render → step 2 SVG

step3:
  p = translate_element(p, "front-side-panel", dx=fba_px, dy=0)
  render → step 3 SVG

step4:
  dart_tip_x = 115 + fba_px          # tip of dart is at the newly-spread side panel edge
  bust_y     = 152                    # bust level in bodice-v1 coordinates
  p = add_dart(p,
    position  = (dart_tip_x, bust_y),
    width     = fba_px * 0.8,
    length    = fba_px,
    angle_deg = 180,                  # dart points LEFT toward CF (angle_deg=180 in SVG y-down)
    dart_id   = "front-bust-dart")
  render → step 4 SVG
```

**Do not use `spread_at_line`.** `spread_at_line` classifies ALL elements in the SVG by centroid position and would incorrectly translate the back pieces. Use `translate_element` directly on `front-side-panel`.

## File layout

```
backend/
  lib/
    cascade/
      __init__.py        (empty)
      types.py           (CascadeStep, CascadeScript, CascadeResult dataclasses)
      fba.py             (apply_fba function)
  routes/
    adjustments.py       (POST /apply-adjustment route)
  tests/
    test_fba_cascade.py
```

Register `adjustments.py` router in `main.py`.

## Acceptance criteria

- [ ] Given `fba_amount_cm=2.5`, `apply_fba` returns a `CascadeResult` with exactly 4 steps.
- [ ] Each step has `step_number`, a non-empty `narration` string, and a valid SVG string.
- [ ] Step 1 SVG parses as valid XML and contains elements `front-cf-panel` and `front-side-panel`.
- [ ] Step 2 SVG contains a `<line id="fba-slash-1">` element.
- [ ] Step 3 SVG: the `front-side-panel` centroid x-coordinate is shifted right by `fba_px` (±1px tolerance) compared to step 2.
- [ ] Step 4 SVG contains a `<polygon id="front-bust-dart">`.
- [ ] `front-cf-panel` x-coordinates are unchanged between steps 1 and 4 (FBA does not affect CF panel).
- [ ] `back-piece` x-coordinates are unchanged between steps 1 and 4 (FBA does not affect back).
- [ ] `adjusted_pattern` is a new Pattern object; the input `pattern` is not mutated.
- [ ] Given `amount_cm=0.4`, `apply_fba` raises `ValueError` with message containing "0.5".
- [ ] Given `amount_cm=6.1`, `apply_fba` raises `ValueError` with message containing "6.0".
- [ ] `POST /apply-adjustment` with `{"pattern_id":"bodice-v1","adjustment_type":"fba","amount_cm":2.5}` returns HTTP 200 with `cascade_script.steps` having length 4.
- [ ] `POST /apply-adjustment` with `amount_cm=0.3` returns HTTP 422.
- [ ] `POST /apply-adjustment` with `pattern_id="nonexistent"` returns HTTP 404.
- [ ] `POST /apply-adjustment` with `adjustment_type="unsupported"` returns HTTP 422.

## Out of scope

- Swayback or any other adjustment type (separate spec 10).
- Pattern grading based on measurements (V1 applies FBA to the size-14 base pattern directly).
- Seam truing after spread (the spread opens a gap; truing the seams is a future improvement).
- Narration generation via Claude (text is hardcoded for V1; Claude narration is a V2 feature).
- PDF export.
- Any modification to the back bodice pieces.

## Technical approach

- New subpackage `backend/lib/cascade/` with `types.py` and `fba.py`.
- `apply_fba` calls existing `pattern_ops` functions only (`load_pattern`, `render_pattern`, `slash_line`, `translate_element`, `add_dart`).
- The route in `adjustments.py` loads the pattern from `REGISTRY`, calls `apply_fba`, serialises the cascade script via Pydantic, and returns it.
- Pydantic response model: `CascadeScriptResponse` with `adjustment_type: str`, `pattern_id: str`, `amount_cm: float`, `steps: list[CascadeStepResponse]`.

## Dependencies

- `backend/lib/pattern_ops.py` — all geometric operations
- `backend/lib/pattern_registry.py` — REGISTRY singleton
- No new third-party packages needed

## Testing approach

- Unit tests in `backend/tests/test_fba_cascade.py`.
- Use the real `bodice-v1.svg` fixture (load from `backend/lib/patterns/bodice-v1/bodice-v1.svg`).
- Verify each acceptance criterion with a dedicated test.
- For SVG content assertions: parse the step SVG with `lxml.etree` and query by element id.
- For coordinate shift assertion: parse polygon points from step-2 and step-3 SVGs, compare centroid x.
- Integration test: hit `POST /apply-adjustment` via `TestClient`.

## Notes for implementer

- The bodice-v1 SVG has been updated to use named polygon elements. All required element IDs exist.
- Bust column is at x=115. Bust level (underarm-to-bust midpoint) is at y=152. These are bodice-v1-specific constants; hardcode them in `fba.py` with a comment explaining they are tied to this pattern's geometry.
- `add_dart` with `angle_deg=180` creates a dart whose TIP is at `position` and whose BASE extends leftward. Calling it with `position=(dart_tip_x, bust_y)` and `angle_deg=180` places the tip at the spread panel edge and the base back at the original bust column — this represents a side-seam bust dart pointing toward the bust point. Verify the geometry with the acceptance criterion tests.
- Do not hardcode narration text as a module-level constant — put the strings inline with the step construction so they're easy to tune later.
- The `cascade/` directory is new; create `backend/lib/cascade/__init__.py` as an empty file.
- Register the new router in `main.py` with `app.include_router(adjustments_router)`.

## Implementation notes

**Branch:** `feat/15-fba-cascade`

### What was implemented

- `backend/lib/cascade/fba.py` — `apply_fba()` function implementing the 4-step FBA cascade.
- `backend/routes/cascades.py` — added `"fba": apply_fba` to the `ADJUSTMENTS` dispatch table.
- `backend/tests/test_fba_cascade.py` — 29 tests (22 unit + 7 integration) covering all acceptance criteria.
- All 392 backend tests pass. Ruff and black linters pass.

### Deviations from spec

1. **No new `routes/adjustments.py` created.** The spec's File Layout section suggests a new `adjustments.py` router, but the explicit task instructions say to add `"fba": apply_fba` to the existing dispatch table in `routes/cascades.py`. This keeps the route at `/cascades/apply-adjustment` (already working) and avoids creating a parallel router. The user's task instructions override the spec layout.

2. **Unknown `adjustment_type` returns HTTP 400, not 422.** The spec acceptance criterion says `adjustment_type="unsupported"` returns HTTP 422, but the existing route returns HTTP 400. Changed the test to assert 400 to avoid breaking the existing `test_unknown_adjustment_type_returns_400` test in `test_routes_cascades.py`. Noted with a comment in the test.

3. **`back-piece` element tested as `back-piece-upper` and `back-piece-lower`.** The spec says "back-piece x-coordinates unchanged" but no element named `back-piece` exists in the SVG — only `back-piece-upper` and `back-piece-lower`. Both are tested individually.

4. **fba_px conversion uses `_PX_PER_CM = 5.0` (not `SCALE = 10.0`).** The spec formula `fba_amount_cm * 10 * 0.5 = fba_amount_cm * 5` equals `PX_PER_CM`, not the swayback `SCALE`. Using the correct value.

5. **`seam_adjustments` is an empty dict `{}`.** Seam truing is explicitly out of scope for V1. The `CascadeScript` dataclass defaults to `{}`, so this is natural.

### Open questions for Steph

- The spec says the endpoint should be `POST /apply-adjustment` (no `/cascades` prefix in the acceptance criteria request examples), but the route lives at `/cascades/apply-adjustment`. Is this intentional? Integration tests use `/cascades/apply-adjustment` and pass.
- Should the `adjustment_type="unsupported"` error be changed to 422 (as the spec says) in a future cleanup? Doing so would require updating the swayback test too.
