# Spec: Measurements Endpoint

**Spec ID:** 04-measurements-endpoint
**Status:** implemented
**Created:** 2026-04-24
**Depends on:** none

## What it does

A FastAPI route (`POST /measurements`) that accepts a user's body measurements, validates them, and returns them normalised. This is the first real product route — it's what runs when the user fills in the measurement form and hits submit. Downstream, the grading engine and SMPL body model will consume this output.

## User-facing behavior

No direct UI (that's spec 05). The calling frontend POSTs a JSON body and gets back validated measurements plus a derived standard size label (e.g. "14", "18W") for reference. If any field is out of range or missing, the response is a 422 with a clear error message per field.

## Inputs and outputs

### Request body (JSON)

| Field | Type | Unit | Valid range | Required |
|-------|------|------|-------------|----------|
| `bust_cm` | float | cm | 60–200 | yes |
| `waist_cm` | float | cm | 40–200 | yes |
| `hip_cm` | float | cm | 60–200 | yes |
| `height_cm` | float | cm | 120–220 | yes |
| `back_length_cm` | float | cm | 30–60 | yes |

### Response body (JSON) — 200 OK

```json
{
  "bust_cm": 96.0,
  "waist_cm": 78.0,
  "hip_cm": 104.0,
  "height_cm": 168.0,
  "back_length_cm": 39.5,
  "size_label": "14"
}
```

### Errors

- `422 Unprocessable Entity` — any field missing or outside valid range; FastAPI/Pydantic provides per-field detail.
- `400 Bad Request` — not used; Pydantic handles all validation.

## Acceptance criteria

- [x] Given a valid body with all 5 fields in range, when `POST /measurements` is called, then the response is `200 OK` with all fields echoed back plus a `size_label`.
- [x] Given `bust_cm: 59` (below minimum), when `POST /measurements` is called, then the response is `422` with an error referencing `bust_cm`.
- [x] Given `bust_cm: 201` (above maximum), when `POST /measurements` is called, then the response is `422`.
- [x] Given a body missing `waist_cm`, when `POST /measurements` is called, then the response is `422`.
- [x] Given `bust_cm: 96, waist_cm: 78, hip_cm: 104`, when `POST /measurements` is called, then `size_label` is `"14"` (see size table below).
- [x] Given measurements that map to a plus size, `size_label` reflects a W label (e.g. `"18W"`).
- [x] `uv run pytest tests/test_measurements.py` passes with all tests green.
- [x] `uv run ruff check . && uv run black --check .` exits 0.

## Out of scope

- Storing measurements in a database or session (return only; caller stores state).
- Inch/metric conversion (cm only for V1).
- Custom ease allowances.
- Half-sizes or petite/tall variants.
- Anything beyond the 5 fields listed.

## Technical approach

**Pydantic models** in `backend/lib/measurements.py` (pure logic, no FastAPI):

```python
class Measurements(BaseModel):
    bust_cm: float = Field(..., ge=60, le=200)
    waist_cm: float = Field(..., ge=40, le=200)
    hip_cm: float = Field(..., ge=60, le=200)
    height_cm: float = Field(..., ge=120, le=220)
    back_length_cm: float = Field(..., ge=30, le=60)

class MeasurementsResponse(Measurements):
    size_label: str
```

**Size label logic** — simple lookup based on bust measurement, British/Australian sizing:

| Bust (cm) | Size label |
|-----------|------------|
| < 83 | "8" |
| 83–87 | "10" |
| 88–92 | "12" |
| 93–97 | "14" |
| 98–102 | "16" |
| 103–107 | "18" |
| 108–112 | "20" |
| 113–117 | "22W" |
| 118–122 | "24W" |
| ≥ 123 | "26W+" |

Pure function `derive_size_label(bust_cm: float) -> str` in `backend/lib/measurements.py`.

**Route** in `backend/routes/measurements.py` — thin handler, calls into lib:

```python
@router.post("/measurements", response_model=MeasurementsResponse)
def create_measurements(body: Measurements) -> MeasurementsResponse:
    return MeasurementsResponse(
        **body.model_dump(),
        size_label=derive_size_label(body.bust_cm),
    )
```

Register under `/` prefix in `backend/main.py` (no prefix — route is `/measurements`).

## Dependencies

- FastAPI, Pydantic (already in `pyproject.toml`)
- No new external packages

## Testing approach

- **Unit tests** in `backend/tests/test_measurements.py`:
  - `derive_size_label` with values at every boundary (82, 83, 87, 88, 92, 93 …)
  - `Measurements` model validation: each field at min, max, just below min, just above max
- **Integration tests** via FastAPI `TestClient`:
  - Happy path (full valid body)
  - Each field missing
  - Each field out of range
  - W-size response

## Open questions

None.

## Implementation notes

### What was implemented

- `backend/lib/measurements.py` — pure Pydantic models (`Measurements`, `MeasurementsResponse`) and `derive_size_label(bust_cm: float) -> str`. No FastAPI imports; fully unit-testable in isolation.
- `backend/routes/measurements.py` — thin FastAPI router, `POST /measurements` registered without a prefix so the route resolves at `/measurements`.
- `backend/main.py` — measurements router registered alongside the existing dev router.
- `backend/tests/test_measurements.py` — 59 tests covering: all `derive_size_label` boundary values (every entry point from the spec table), each `Measurements` field at min/max/just-below-min/just-above-max, and integration tests via `TestClient` for happy path, all missing fields, and all out-of-range fields.

### Deviations from spec

None. Implementation matches the spec exactly, including the exact size table, field constraints, and response shape.

### Open questions for Steph

None.

### New ADRs

None required — no architectural decisions beyond what was specified.

## Cleanup notes

- Checkboxes marked: 8 of 8
- Stray files removed: none found
- TODOs resolved: none found; none surfaced
- Linter/test result: PASS — 158 tests pass, ruff+black exit 0
- Items for Steph's attention before `/review`: none

## Notes for implementer

- Keep `backend/lib/measurements.py` free of FastAPI imports — pure Pydantic + Python only.
- Register the measurements router in `backend/main.py` alongside the existing dev router.
- Size label table is intentionally simple — it's for display only, not for grading logic. Grading uses raw measurements directly.
- Run cleanup checklist after implementation (see `.claude/commands/cleanup.md`).
