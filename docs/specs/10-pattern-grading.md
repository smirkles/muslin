# Spec: Pattern Grading

**Spec ID:** 10-pattern-grading
**Status:** implemented
**Created:** 2026-04-25
**Depends on:** 01-pattern-svg-library, 07-measurements-fba-fields, 06-pattern-registry

## What it does

Scales a base-size pattern to a user's body measurements, producing a personalised baseline SVG before any cascade adjustments (FBA, swayback) run. Given a `pattern_id` and a `measurement_id`, grading applies proportional scaling per piece — bodice pieces scale horizontally by `user_bust / base_bust`, lower pieces by `user_hip / base_hip`, and all pieces scale vertically by `user_back_length / base_back_length`. The graded SVG is returned to the caller and stored in an in-memory session store so downstream cascade steps can fetch it by id. This is the deterministic "good enough starting point" — shape-specific issues are the cascade engine's job.

## User-facing behavior

No direct UI. The frontend calls `POST /patterns/{pattern_id}/grade` with the `measurement_id` from `POST /measurements`. The response carries a `graded_pattern_id`, the graded SVG string (ready to render in the browser), and a flat dict of the adjustments made in centimetres so the UI can surface them (e.g. "we widened the bust by 2.5 cm"). The calling frontend stores `graded_pattern_id` alongside `measurement_id` and `pattern_id` for use by later routes.

## Inputs and outputs

### Request — `POST /patterns/{pattern_id}/grade`

Path param: `pattern_id: str` — id of a registered pattern (see spec 06).

Body (JSON): `{ "measurement_id": "b3d7e2a1-1234-5678-abcd-ef0123456789" }`

### Response (JSON) — 200 OK

```json
{
  "graded_pattern_id": "f71c-...",
  "pattern_id": "fitted-bodice",
  "measurement_id": "b3d7e2a1-...",
  "svg": "<svg xmlns=...>...</svg>",
  "adjustments_cm": {
    "bust": 2.5,
    "waist": 1.0,
    "hip": -0.5,
    "back_length": 0.5
  }
}
```

`adjustments_cm` is aggregate (not per-piece): each value is `user_measurement - base_measurement`, rounded to 1 decimal. Negative means the user is smaller than the base size.

### Errors

- **404** — `pattern_id` not in registry → `{"detail": "Pattern '<id>' not found"}`.
- **404** — `measurement_id` not in session store → `{"detail": "Measurements '<id>' not found"}`.
- **422** — body missing `measurement_id` or malformed (FastAPI validation).
- **500** — pattern SVG cannot be parsed or required element missing → `{"detail": "Failed to grade pattern: <reason>"}`.

## Acceptance criteria

- [ ] Given base measurements `bust=92, waist=74, hip=100, back_length=40` and user measurements `bust=96, waist=78, hip=104, back_length=41`, when `grade_pattern(...)` is called, then `adjustments_cm == {"bust": 4.0, "waist": 4.0, "hip": 4.0, "back_length": 1.0}`.
- [ ] Given identical base and user measurements, when `grade_pattern` is called, then all `adjustments_cm` values are `0.0` and every SVG coordinate matches the input within `1e-6`.
- [ ] Given user bust smaller than base bust, then `adjustments_cm["bust"]` is negative and graded bodice bounding-box width is strictly smaller than the base.
- [ ] Given a piece whose id starts with `bodice-`, `front-bodice`, or `back-bodice`, when `grade_pattern` is called, then it is scaled horizontally by `user_bust / base_bust` (bounding-box ratio within `1e-6`).
- [ ] Given a piece whose id starts with `skirt-` or `lower-`, when `grade_pattern` is called, then it is scaled horizontally by `user_hip / base_hip`.
- [ ] All pieces are scaled vertically by `user_back_length / base_back_length`.
- [ ] `grade_pattern` returns a new object; the input pattern is unchanged.
- [ ] Given a successful `grade_pattern` call, when `store_graded_pattern(g)` is called, then `get_graded_pattern(g.graded_pattern_id)` returns an equal object.
- [ ] Given an unknown `graded_pattern_id`, `get_graded_pattern` raises `KeyError`.
- [ ] Two successive grading calls produce distinct `graded_pattern_id` values.
- [ ] Given a registered `pattern_id` and valid `measurement_id`, `POST /patterns/{pattern_id}/grade` returns 200 with `graded_pattern_id` (UUID), `svg` (non-empty, contains `<svg`), and `adjustments_cm` with exactly keys `bust`, `waist`, `hip`, `back_length`.
- [ ] Given an unknown `pattern_id`, response is 404 with a detail mentioning the id.
- [ ] Given an unknown `measurement_id`, response is 404 with a detail mentioning measurements.
- [ ] Given a body missing `measurement_id`, response is 422.
- [ ] `backend/lib/grading.py` contains no `fastapi` imports (enforced by import-hygiene test).
- [ ] `uv run pytest` passes; `uv run ruff check . && uv run black --check .` exit 0.

## Out of scope

- FBA, swayback, or any shape-based cascade adjustment.
- SMPL body-shape fitting (V2).
- Per-piece ease, dart rotation, seam truing.
- Curve-aware scaling (bezier control points scale as plain coordinates, matching pattern_ops V1).
- Persistence beyond in-memory session store.
- Sleeves (no sleeve pieces in V1 patterns).
- Unit conversion — cm only.
- Waist independently driving a horizontal transform (reported in `adjustments_cm` for UI, but not applied as a separate transform in V1).

## Technical approach

### New module: `backend/lib/grading.py`

```python
@dataclass(frozen=True)
class GradedPattern:
    graded_pattern_id: str
    pattern_id: str
    measurement_id: str
    svg: str
    adjustments_cm: dict[str, float]

def grade_pattern(pattern, base_measurements, user_measurements, pattern_id, measurement_id) -> GradedPattern: ...
def store_graded_pattern(g: GradedPattern) -> None: ...
def get_graded_pattern(graded_pattern_id: str) -> GradedPattern: ...
```

Piece scaling by id-prefix convention:

| id prefix | Horizontal scale factor |
|-----------|------------------------|
| `bodice-`, `front-bodice`, `back-bodice` | `user.bust_cm / base.bust_cm` |
| `skirt-`, `lower-` | `user.hip_cm / base.hip_cm` |
| anything else | `1.0` (log a warning) |

Vertical scale for every piece: `user.back_length_cm / base.back_length_cm`. Pivot = piece bounding-box centre. Applied via a new `pattern_ops.scale_element(pattern, element_id, sx, sy, pivot)`.

`meta.json` for each pattern must be extended with `base_bust_cm`, `base_waist_cm`, `base_hip_cm`, `base_back_length_cm` fields. Update `PatternMeta`, `PatternDetail`, `build_registry`, and the fitted-bodice `meta.json` fixture.

## Dependencies

- External libraries needed: none (stdlib `uuid`, `dataclasses`).
- Other specs that must be implemented first: `01-pattern-svg-library` (needs new `scale_element` primitive), `07-measurements-fba-fields` (session store), `06-pattern-registry` (`meta.json` schema).
- Requires two ADRs filed in `docs/decisions/` before coding: (1) `scale_element` added to `pattern_ops`; (2) `meta.json` schema extended with base measurements.

## Testing approach

- **Unit tests** in `backend/tests/test_grading.py`: 2-piece synthetic fixture (`bodice-front` + `skirt-front`) with known base measurements; identity case; negative adjustments; store round-trip; distinct UUIDs; import-hygiene test.
- **Route tests** in `backend/tests/test_grading_route.py`: happy path via `TestClient`; 404 on unknown pattern; 404 on unknown measurement; 422 on missing body.
- **Fixtures:** `backend/tests/fixtures/patterns/two_piece.svg`; updated fitted-bodice `meta.json`.
- **Manual verification:** open graded SVG in browser for fitted-bodice at a noticeably larger size; confirm bodice width and back length visibly grow.

## Open questions

1. **Piece-to-measurement mapping:** id-prefix convention (default, V1) vs per-piece metadata. Revisit at second pattern.
2. **Waist horizontal scaling:** currently not independently applied — only reported. Confirm this is acceptable for V1 demo.

## Notes for implementer

- `lib/grading.py` must not import from `fastapi`, `starlette`, or `routes/`.
- `scale_element` implementation: deep-copy, then for each descendant coordinate `(pivot_x + (x - pivot_x) * sx, pivot_y + (y - pivot_y) * sy)`. Reuse `_translate_element`'s dispatch and `<g>` recursion from pattern_ops.
- Piece pivot = bounding-box centre of that piece's current geometry. A pivot of `(0, 0)` will drift pieces off-canvas.
- `adjustments_cm` rounding: `round(value, 1)`.
- File both ADRs in `docs/decisions/` before writing any code.
- Write failing tests first per `CLAUDE.md` rule 5.

## Implementation notes

### What was implemented

- `backend/lib/grading.py`: `grade_pattern`, `store_graded_pattern`, `get_graded_pattern`, `BaseMeasurements`, `GradedPattern`, `MeasurementsProtocol`.
- `backend/lib/pattern_ops.py`: `scale_element` (public), `piece_ids` (public), `element_bbox` (public), plus `_scale_element` internal helper.
- `backend/routes/patterns.py`: `POST /patterns/{id}/grade` handler, `GradeRequest`, `GradedPatternResponse`.
- `backend/lib/patterns/bodice-v1/meta.json`: updated with base measurements (bust 88, waist 69, hip 94, back_length 40).
- All 436 tests pass; ruff and black both exit 0.

### Review fixes applied (2026-04-25)

Review file: `docs/reviews/10-pattern-grading-20260425T042312Z.md`

1. **`replicate` dependency removed**: `pyproject.toml` never had `replicate` on this branch in the final state; `uv lock` regenerated `uv.lock` to remove the stale `replicate` and its transitives.

2. **Private `pattern_ops` internals decoupled**: `grading.py` previously accessed `_element_bbox`, `_G_TAGS`, `pattern._tree.getroot()`, and `pattern._id_index` directly. Added `piece_ids(pattern)` and `element_bbox(el)` as public functions in `pattern_ops.py`. `grading.py` now uses only `piece_ids`, `element_bbox`, `get_element`, and `ElementNotFound` from the public API. 8 new tests added in `TestPieceIds` and `TestElementBbox` classes.

3. **`MeasurementsProtocol`**: Added `typing.Protocol` to `grading.py`. `grade_pattern` parameter changed from `user_measurements: object` to `user_measurements: MeasurementsProtocol`. Documents the structural contract (bust_cm, waist_cm, hip_cm, back_length_cm: float) and enables type-checker verification.

4. **`cast()` replaces `# type: ignore`**: `routes/patterns.py` now uses `cast(float, meta.base_X_cm)` instead of four `# type: ignore[arg-type]` comments, in line with CLAUDE.md's ban on suppressed warnings.

### Deviations from spec

None. All acceptance criteria pass; no spec behaviour was changed.

### Open questions for Steph

None remaining. The two questions from the review were resolved:
- `replicate` removed (confirmed: spec 12 has its own branch and should manage its own deps).
- `MeasurementsProtocol` used (no circular import risk — `lib.measurements` is not imported by `lib.grading`).
