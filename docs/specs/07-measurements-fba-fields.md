# Spec: Measurements — FBA Fields, Session Store, and translate_element Fix

**Spec ID:** 07-measurements-fba-fields
**Status:** implemented
**Created:** 2026-04-24
**Depends on:** 04-measurements-endpoint, 01-pattern-svg-library

## What it does

Three tightly coupled changes to the backend measurement and pattern-ops layer:

1. **Add FBA fields** — extend the `Measurements` Pydantic model with `high_bust_cm` and `apex_to_apex_cm`. Both are required for Full Bust Adjustment (FBA). Without them the cascade engine cannot rotate darts correctly.

2. **Add `measurement_id` session store** — `POST /measurements` now returns a UUID `measurement_id`. An in-memory dict maps that UUID to the stored `Measurements` object. Downstream endpoints (diagnose, apply-adjustment) pass only the `measurement_id` rather than re-POSTing the full measurements every call.

3. **Fix `translate_element` on `<g>`** — currently a silent no-op. It must recurse into all direct children and apply the translation. The existing no-op behaviour corrupts any cascade that targets a whole pattern piece (a `<g>`).

## Inputs and outputs

### Updated `POST /measurements` request body

| Field | Type | Unit | Valid range | Required |
|-------|------|------|-------------|----------|
| `bust_cm` | float | cm | 60–200 | yes |
| `high_bust_cm` | float | cm | 60–200 | yes |
| `apex_to_apex_cm` | float | cm | 10–30 | yes |
| `waist_cm` | float | cm | 40–200 | yes |
| `hip_cm` | float | cm | 60–200 | yes |
| `height_cm` | float | cm | 120–220 | yes |
| `back_length_cm` | float | cm | 30–60 | yes |

### Updated `POST /measurements` response body — 200 OK

```json
{
  "measurement_id": "b3d7e2a1-1234-5678-abcd-ef0123456789",
  "bust_cm": 96.0,
  "high_bust_cm": 90.0,
  "apex_to_apex_cm": 18.5,
  "waist_cm": 78.0,
  "hip_cm": 104.0,
  "height_cm": 168.0,
  "back_length_cm": 39.5,
  "size_label": "14"
}
```

### Session store

- Module-level `dict[str, MeasurementsResponse]` in `backend/lib/measurements.py`.
- Key: UUID string. Value: the full `MeasurementsResponse` (including all fields + size_label).
- `store_measurements(m: MeasurementsResponse) -> str` — stores m, returns the UUID key.
- `get_measurements(measurement_id: str) -> MeasurementsResponse` — raises `KeyError` if not found.
- **In-memory only** — data is lost on server restart. This is intentional for V1 (hackathon); no persistence layer needed.

### Fixed `translate_element` on `<g>`

Current behaviour (bug): `translate_element(pattern, g_id, dx, dy)` detects tag `<g>` and returns the Pattern unchanged.

New behaviour: recurse into all direct child elements of the `<g>` and apply `(dx, dy)` translation to each. Child elements may be `<path>`, `<polygon>`, `<line>`, `<text>` — use the existing dispatch logic already implemented for those types.

Grandchildren (nested `<g>`) should also be handled recursively by the same mechanism (since the dispatch will again hit the `<g>` branch, which now recurses).

## Acceptance criteria

### FBA fields

- [ ] Given a valid body with all 7 fields, when `POST /measurements` is called, then the response is `200 OK` with all 7 fields echoed back, a `size_label`, and a `measurement_id` UUID string.
- [ ] Given `high_bust_cm: 59` (below minimum), when `POST /measurements` is called, then the response is `422` with an error referencing `high_bust_cm`.
- [ ] Given `apex_to_apex_cm: 9` (below minimum of 10), when `POST /measurements` is called, then the response is `422` with an error referencing `apex_to_apex_cm`.
- [ ] Given `apex_to_apex_cm: 31` (above maximum of 30), when `POST /measurements` is called, then the response is `422`.
- [ ] Given a body missing `high_bust_cm`, when `POST /measurements` is called, then the response is `422`.
- [ ] Given a body missing `apex_to_apex_cm`, when `POST /measurements` is called, then the response is `422`.

### Session store

- [ ] Given a successful `POST /measurements`, when `get_measurements(measurement_id)` is called with the returned UUID, then it returns a `MeasurementsResponse` with all 7 fields matching the request.
- [ ] Given an unknown UUID, when `get_measurements` is called, then it raises `KeyError`.
- [ ] Two successive `POST /measurements` calls with different bodies return different `measurement_id` values, and each UUID returns its own data.

### translate_element fix

- [ ] Given a Pattern with a `<g id="piece">` containing two `<path>` children, when `translate_element(p, "piece", 10, 5)` is called, then each child path's coordinates are shifted by (10, 5). The original Pattern is unchanged.
- [ ] Given a Pattern with a `<g>` containing a nested `<g>` containing a `<path>`, when `translate_element` is called on the outer `<g>`, then the innermost path's coordinates are also shifted.
- [ ] Given a Pattern with a `<g id="piece">` and a separate `<path id="other">`, when `translate_element(p, "piece", 10, 5)` is called, then the `other` path's coordinates are unchanged.
- [ ] Existing tests for `translate_element` on `<path>`, `<polygon>`, `<line>` still pass.

### General

- [ ] `uv run pytest tests/test_measurements.py` passes with all tests green (including regression tests for the existing 5-field happy path — the new fields are additive).
- [ ] `uv run pytest tests/test_pattern_ops.py` passes with all tests green.
- [ ] `uv run ruff check . && uv run black --check .` exits 0.

## Out of scope

- Persisting measurements to a database or file.
- Eviction/expiry of old session store entries.
- A `GET /measurements/{measurement_id}` retrieval endpoint (not needed until diagnosis route is wired).
- Changing `size_label` logic.
- Any frontend changes (those are in spec 05).

## Technical approach

### Measurements model extension

In `backend/lib/measurements.py`:

```python
class Measurements(BaseModel):
    bust_cm: float = Field(..., ge=60, le=200)
    high_bust_cm: float = Field(..., ge=60, le=200)
    apex_to_apex_cm: float = Field(..., ge=10, le=30)
    waist_cm: float = Field(..., ge=40, le=200)
    hip_cm: float = Field(..., ge=60, le=200)
    height_cm: float = Field(..., ge=120, le=220)
    back_length_cm: float = Field(..., ge=30, le=60)

class MeasurementsResponse(Measurements):
    measurement_id: str
    size_label: str
```

### Session store

In `backend/lib/measurements.py`:

```python
import uuid

_store: dict[str, MeasurementsResponse] = {}

def store_measurements(m: MeasurementsResponse) -> str:
    """Store measurements and return their UUID key."""
    key = str(uuid.uuid4())
    _store[key] = m
    return key

def get_measurements(measurement_id: str) -> MeasurementsResponse:
    """Retrieve stored measurements by UUID. Raises KeyError if not found."""
    return _store[measurement_id]
```

### Route update

In `backend/routes/measurements.py`:

```python
@router.post("/measurements", response_model=MeasurementsResponse)
def create_measurements(body: Measurements) -> MeasurementsResponse:
    response = MeasurementsResponse(
        **body.model_dump(),
        size_label=derive_size_label(body.bust_cm),
        measurement_id="",  # placeholder; filled by store
    )
    measurement_id = store_measurements(response)
    return response.model_copy(update={"measurement_id": measurement_id})
```

### translate_element fix

In `backend/lib/pattern_ops.py`, the `<g>` branch of `translate_element` currently reads:

```python
# no-op for groups
return pattern
```

Replace with:

```python
# Recurse into direct children
new_pattern = pattern
for child in list(el):
    child_id = child.get("id")
    if child_id:
        new_pattern = translate_element(new_pattern, child_id, dx, dy)
    else:
        # Child has no id — translate it directly in-place on the copy
        _translate_element_inplace(new_pattern._root.find(f".//*[@id='{element_id}']"), child, dx, dy)
return new_pattern
```

Simpler alternative (preferred): rebuild the `_id_index` to include un-id'd elements too, or just iterate children by reference after deep copy. The key contract is that all geometric coordinates in all descendants shift by (dx, dy).

Implementation note: since `translate_element` operates on a deep copy, the implementer can deep-copy the pattern, then walk the `<g>`'s children in the copy and apply coordinate transforms in-place (using the existing single-element helpers) rather than calling `translate_element` recursively with IDs. Either approach is fine; recursive-by-ID is cleaner if all children have IDs (which fixture SVGs should guarantee).

## Dependencies

- FastAPI, Pydantic (already in `pyproject.toml`)
- `uuid` from stdlib
- No new packages

## Testing approach

### Measurements tests (`backend/tests/test_measurements.py`)

Add tests for:
- `high_bust_cm` and `apex_to_apex_cm` at min, max, just-below-min, just-above-max
- Both fields missing from request body
- `measurement_id` is a valid UUID string in response
- `get_measurements` round-trip: store then retrieve
- Two POSTs return distinct `measurement_id` values

Keep all existing tests passing (they test the 5 original fields; the new fields just extend the model).

### Pattern ops tests (`backend/tests/test_pattern_ops.py`)

Add tests for:
- `<g>` with two `<path>` children translated correctly
- Nested `<g>` recursion
- Sibling elements NOT translated when only the `<g>` is targeted
- Existing tests for `<path>`, `<polygon>`, `<line>` translation still pass

## Open questions

None. Ready for implementation.

## Implementation notes

### What was implemented

- `backend/lib/measurements.py` — added `high_bust_cm` (60–200) and `apex_to_apex_cm` (10–30) fields to `Measurements`. Added `measurement_id: str` to `MeasurementsResponse`. Added module-level `_store: dict[str, MeasurementsResponse]`, `store_measurements()`, and `get_measurements()`.
- `backend/routes/measurements.py` — route now calls `store_measurements()` and returns `measurement_id` in response via `model_copy`.
- `backend/lib/pattern_ops.py` — fixed `_translate_element` on `<g>`: now recurses into all direct children using `for child in el: _translate_element(child, dx, dy)`. Handles nested `<g>` automatically via recursion.
- `backend/tests/test_measurements.py` — updated `_valid_payload()` and `_valid_body()` helpers to include both new fields. Added `TestFBAFields` (12 tests) and `TestMeasurementId` (5 tests).
- `backend/tests/test_pattern_ops.py` — added `TestTranslateGroup` (5 tests) and `grouped_piece.svg` fixture.

### Deviations from spec

None. All acceptance criteria implemented as specified.

### Test results

208 tests pass. `ruff check` and `black --check` both exit 0.

## Notes for implementer

- The existing 5-field test suite in `test_measurements.py` must stay green. The new fields are additive — existing valid requests without `high_bust_cm`/`apex_to_apex_cm` will now fail with 422 (correct, since they're required). Update any test fixtures that send 5-field bodies to include the 2 new fields.
- `size_label` is still derived from `bust_cm` only — do not change that logic.
- For the `translate_element` fix, add at least one fixture SVG with a `<g>` containing multiple children to `backend/tests/fixtures/patterns/`. The existing `with_dart.svg` may already have this structure — check before creating a new file.
- Run cleanup checklist after implementation (see `.claude/commands/cleanup.md`).
