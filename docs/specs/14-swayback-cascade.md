# Spec: Swayback Cascade

**Spec ID:** 14-swayback-cascade
**Status:** ready-for-implementation
**Created:** 2026-04-25
**Depends on:** 01-pattern-svg-library, 06-pattern-registry

## What it does

Applies a swayback adjustment to the back bodice piece and produces a cascade script for the frontend animation engine. A swayback adjustment removes excess fabric at the centre back waist for people with a pronounced inward lumbar curve (who otherwise get pooling/rippling at the lower back of a fitted garment). The technique: draw a horizontal fold line at the waist, rotate the lower back section upward so the wedge closes at centre back and tapers to zero at the side seam, then true the resulting uneven seams. This spec also establishes the shared cascade infrastructure (`CascadeResult`, `CascadeScript`, `/apply-adjustment` route) that the FBA cascade (spec 15) will build on.

## User-facing behavior

No direct user interaction. The frontend calls `POST /cascades/apply-adjustment` with `{"adjustment_type": "swayback", "amount_cm": 1.5}`. The response carries a cascade script JSON that the `CascadePlayer` component (spec 13) animates step-by-step.

## Inputs and outputs

### `apply_swayback` function

```python
# backend/lib/cascade/swayback.py
def apply_swayback(
    pattern: Pattern,
    swayback_amount_cm: float,
    pattern_id: str = "bodice-v1",
) -> CascadeResult
```

- `pattern` — loaded from bodice-v1 SVG. Must contain: `back-piece-upper`, `back-piece-lower`, `back-cb-seam`, `back-side-seam`, `back-waist-seam`, `back-cb-seam-reference`, `back-side-seam-reference`.
- `swayback_amount_cm` — valid range `0.5–2.5`. Values outside raise `ValueError`.

### Shared types — `backend/lib/cascade/types.py` (NEW, established by this spec)

```python
@dataclass(frozen=True)
class CascadeStep:
    step_number: int
    narration: str
    svg: str          # full SVG string for this step's state

@dataclass
class CascadeScript:
    adjustment_type: str
    pattern_id: str
    amount_cm: float
    steps: list[CascadeStep]
    seam_adjustments: dict[str, float] = field(default_factory=dict)

@dataclass
class CascadeResult:
    adjusted_pattern: Pattern
    cascade_script: CascadeScript
```

### HTTP endpoint — `POST /cascades/apply-adjustment`

Request:
```json
{"pattern_id": "bodice-v1", "adjustment_type": "swayback", "amount_cm": 1.5}
```

Response (200):
```json
{
  "adjustment_type": "swayback",
  "pattern_id": "bodice-v1",
  "amount_cm": 1.5,
  "steps": [
    {"step_number": 1, "narration": "...", "svg": "<svg ...>...</svg>"}
  ],
  "seam_adjustments": {
    "cb_seam_delta_cm": -1.5,
    "side_seam_delta_cm": 0.0,
    "waist_seam_delta_cm": -0.45
  }
}
```

### Errors

- **422** — `amount_cm` outside `[0.5, 2.5]` → `{"detail": "swayback_amount_cm must be between 0.5 and 2.5"}`.
- **404** — `pattern_id` not in registry → `{"detail": "Pattern '<id>' not found"}`.
- **400** — `adjustment_type` not recognised → `{"detail": "Unknown adjustment type: '<type>'"}`.
- **500** — pattern missing a required element → `{"detail": "Pattern element '<id>' not found"}`.

## Cascade steps

`apply_swayback` produces **exactly 5 steps**. Narration loaded from `prompts/swayback/v1_baseline.md`.

| Step | What changes | Narration key |
|------|-------------|---------------|
| 1 | Base pattern (no transforms) | `step_1_intro` |
| 2 | Fold line drawn at waist across full back | `step_2_fold_line` |
| 3 | `back-piece-lower` rotated around side-seam pivot | `step_3_fold_wedge` (uses `{amount_cm}`) |
| 4 | Side seam trued | `step_4_true_side_seam` |
| 5 | CB seam trued | `step_5_true_cb_seam` |

### Algorithm

```python
SCALE = 10 * 0.5           # cm → px (matches pattern_ops convention)
CB_X, SIDE_SEAM_X = 210, 390
WAIST_Y = 160

swayback_px = swayback_amount_cm * SCALE
angle_deg   = -math.degrees(math.atan2(swayback_px, SIDE_SEAM_X - CB_X))
pivot       = (SIDE_SEAM_X, WAIST_Y)

step1: render base
step2: slash_line(pattern, (CB_X, WAIST_Y), (SIDE_SEAM_X, WAIST_Y), "swayback-fold-line")
step3: rotate_element(pattern, "back-piece-lower", angle_deg, pivot)
step4: true_seam_length(pattern, "back-side-seam", "back-side-seam-reference")
step5: true_seam_length(pattern, "back-cb-seam",   "back-cb-seam-reference")
```

Rotation, not translation: rotation around the side-seam pivot keeps side-seam length invariant. Translation is geometrically wrong.

### Narration prompt file — `prompts/swayback/v1_baseline.md`

```markdown
## step_1_intro
Starting with your size-graded back bodice.

## step_2_fold_line
We draw a horizontal fold line at the waist — this is where we'll take out the excess.

## step_3_fold_wedge
Folding out {amount_cm} cm at centre back closes the gap where excess fabric pools.

## step_4_true_side_seam
We smooth the side seam back into a single clean line.

## step_5_true_cb_seam
And we straighten the centre back. Your adjusted back piece is ready.
```

Loader: `backend/lib/cascade/prompts.py` — `load_narration(cascade_name, version="v1_baseline") -> dict[str, str]`. Regex on `^## (\w+)` for section keys. `{amount_cm}` substituted via `str.format` at call site.

## Acceptance criteria

- [ ] Given `swayback_amount_cm=1.5`, `apply_swayback` returns a `CascadeResult` with exactly 5 steps.
- [ ] Each step has a non-empty `narration` and a valid SVG string that parses as XML.
- [ ] Narration in each step matches the corresponding key from `prompts/swayback/v1_baseline.md`, with `{amount_cm}` substituted.
- [ ] Step 2 SVG contains `<line id="swayback-fold-line">` with y-coordinate equal to `WAIST_Y` (160).
- [ ] Step 3: `back-piece-lower` centroid y is less than in step 2 by approximately `swayback_px / 2` (±2 px).
- [ ] Step 3: the rotated `back-piece-lower` still contains a point within 1 px of the pivot `(SIDE_SEAM_X, WAIST_Y)`.
- [ ] Step 4: `back-side-seam` endpoint x-coordinate is within 1 px of `SIDE_SEAM_X`.
- [ ] Step 5: `back-cb-seam` endpoint x-coordinate is within 1 px of `CB_X`.
- [ ] Front elements (any element with id starting `front-`) are byte-identical between step 1 and step 5.
- [ ] `apply_swayback` does not mutate the input pattern (`render_pattern(input)` before and after is equal).
- [ ] `cascade_script.seam_adjustments` has exactly keys `cb_seam_delta_cm`, `side_seam_delta_cm`, `waist_seam_delta_cm`, all floats.
- [ ] `seam_adjustments["cb_seam_delta_cm"]` equals `-swayback_amount_cm` (±0.01).
- [ ] `seam_adjustments["side_seam_delta_cm"]` equals `0.0` (±0.01).
- [ ] Given `swayback_amount_cm=0.4`, `apply_swayback` raises `ValueError` mentioning `"0.5"`.
- [ ] Given `swayback_amount_cm=2.6`, `apply_swayback` raises `ValueError` mentioning `"2.5"`.
- [ ] `load_narration("swayback")` returns dict with exactly 5 keys matching the step names above.
- [ ] `load_narration("swayback")` raises `FileNotFoundError` with the attempted path when the file is missing.
- [ ] `POST /cascades/apply-adjustment` with `adjustment_type:"swayback", amount_cm:1.5` returns HTTP 200 with 5 steps.
- [ ] `POST /cascades/apply-adjustment` with `amount_cm:0.3` returns HTTP 422 mentioning `"0.5"`.
- [ ] `POST /cascades/apply-adjustment` with `amount_cm:3.0` returns HTTP 422 mentioning `"2.5"`.
- [ ] `POST /cascades/apply-adjustment` with `adjustment_type:"unknown"` returns HTTP 400.
- [ ] Response JSON includes `seam_adjustments` dict at top level.
- [ ] `backend/lib/cascade/` contains no `fastapi` imports (import-hygiene test).
- [ ] `uv run pytest` passes; `uv run ruff check . && uv run black --check .` exit 0.

## Out of scope

- FBA or any other cascade type (spec 15).
- Claude-generated narration (static file only in V1).
- Multiple swayback technique variants.
- Curved back seams or princess seams.
- Back waist dart rotation (V1 bodice has no back dart).
- PDF export.
- Any modification to front bodice pieces.
- Pattern grading (apply to base size; grading is spec 10).

## Technical approach

- `backend/lib/cascade/types.py` — `CascadeStep`, `CascadeScript`, `CascadeResult` dataclasses. Established by this spec; spec 15 (FBA) will import from here without modification.
- `backend/lib/cascade/swayback.py` — `apply_swayback`.
- `backend/lib/cascade/prompts.py` — `load_narration`.
- `backend/routes/cascades.py` — new router at `/cascades`. `POST /cascades/apply-adjustment` dispatches on `adjustment_type` via dict `{"swayback": apply_swayback}`. Adding FBA in spec 15 is a one-liner to this dict.
- `backend/lib/patterns/bodice-v1/bodice-v1.svg` — upgraded to add back-piece sub-elements (see Notes).
- No new external libraries needed.

## Dependencies

- External libraries: none (all pattern_ops primitives already in spec 01).
- Other specs first: `01-pattern-svg-library` (primitives), `06-pattern-registry` (pattern loading).
- Note: the stray file `docs/specs/09-fba-cascade.md` on disk predates this spec and uses conflicting numbering. It will be renumbered to `15-fba-cascade.md` before implementation. This spec does NOT depend on it.

## Testing approach

- **Unit tests** in `backend/tests/test_swayback_cascade.py`: all acceptance criteria above. Parse step SVGs with `lxml.etree`; compute centroids/endpoints with small test helpers.
- **Narration tests** in `backend/tests/test_cascade_prompts.py`: `load_narration` happy path (tmp fixture file), missing file error.
- **Route tests** in `backend/tests/test_routes_cascades.py`: 200 happy path, 422 out-of-range, 404 unknown pattern, 400 unknown type. Use `TestClient`.
- **Import-hygiene test**: `backend/lib/cascade/` has no `fastapi` transitive imports.
- **Manual verification**: run `POST /cascades/apply-adjustment` with swayback 1.5; feed the cascade script into the `CascadePlayer` component; confirm 5 animated steps in the browser.

## Open questions

1. **`seam_adjustments` placement:** on `CascadeScript` (recommended, top-level in response) vs on the final `CascadeStep`. Chosen: `CascadeScript`. FBA will leave it as an empty dict.
2. **Bodice-v1 back element naming:** names above (`back-piece-upper`, `back-piece-lower`, etc.) are proposed by this spec. If pattern_ops tests already use different names, align before committing.

## Notes for implementer

- **Bodice-v1 SVG upgrade:** current file is a 2-rect placeholder. Need to add `back-piece-upper`, `back-piece-lower`, `back-cb-seam`, `back-side-seam`, `back-waist-seam`, plus invisible reference seams `back-cb-seam-reference` and `back-side-seam-reference` (`display="none"`). Do NOT break existing front-piece element IDs that pattern_ops tests rely on.
- **Rotation sign:** negative = counter-clockwise in SVG y-down coordinates = "fold up" at CB. The pivot-invariant and centroid-moved-up tests will catch a wrong sign.
- **Narration loader is intentionally dumb:** regex on `^## (\w+)`, body = text between headers. No Jinja, no markdown parsing.
- **Dispatch dict pattern:** `ADJUSTMENTS = {"swayback": apply_swayback}` in `routes/cascades.py`. Spec 15 adds `"fba": apply_fba`.
- **Coordinate constants** `CB_X=210`, `SIDE_SEAM_X=390`, `WAIST_Y=160` are tied to bodice-v1's current viewBox. Co-locate them in a `backend/lib/cascade/constants.py` module so both cascades share them.
- Write failing tests first per `CLAUDE.md` rule 5.
