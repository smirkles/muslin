# Spec: Pattern Registry

**Spec ID:** 06-pattern-registry
**Status:** implemented
**Created:** 2026-04-24
**Depends on:** 01-pattern-svg-library

## What it does

An in-memory registry of available sewing patterns plus two FastAPI routes (`GET /patterns` and `GET /patterns/{pattern_id}`) that let the frontend list and load them. This is the first step of the demo flow — before a user can do anything, they pick a pattern to work with.

For V1 the registry is hardcoded with a single placeholder pattern (a minimal valid bodice SVG). The real bodice SVG will be dropped in later without changing any code.

## User-facing behavior

Calling code (the frontend pattern picker) sees:

- `GET /patterns` → list of available patterns with metadata (id, name, description, piece count).
- `GET /patterns/{pattern_id}` → full pattern metadata plus the SVG content as a string.
- `GET /patterns/nonexistent` → 404 with a clear error message.

## Inputs and outputs

### `GET /patterns`

No input.

Response — `200 OK`:
```json
[
  {
    "id": "bodice-v1",
    "name": "Basic Fitted Bodice",
    "description": "A simple fitted bodice block. Good starting point for FBA and swayback adjustments.",
    "piece_count": 2
  }
]
```

### `GET /patterns/{pattern_id}`

Path param: `pattern_id: str`

Response — `200 OK`:
```json
{
  "id": "bodice-v1",
  "name": "Basic Fitted Bodice",
  "description": "A simple fitted bodice block. Good starting point for FBA and swayback adjustments.",
  "piece_count": 2,
  "svg": "<svg ...>...</svg>"
}
```

Response — `404 Not Found`:
```json
{"detail": "Pattern 'unknown-id' not found"}
```

## Acceptance criteria

- [x] `GET /patterns` returns `200` with a list containing at least one pattern entry.
- [x] Each entry in the list has `id`, `name`, `description`, `piece_count`.
- [x] `GET /patterns/bodice-v1` returns `200` with full metadata plus an `svg` field containing a non-empty string.
- [x] The `svg` field parses as valid SVG (has an `<svg>` root element).
- [x] `GET /patterns/nonexistent` returns `404` with a `detail` message naming the unknown id.
- [x] `uv run pytest tests/test_pattern_registry.py` passes with all tests green.
- [x] `uv run ruff check . && uv run black --check .` exits 0.
- [x] All previously passing tests still pass.

## Out of scope

- Loading patterns from disk at request time (registry is built at startup).
- User-uploaded patterns.
- Pattern versioning.
- Pagination of the pattern list.
- Any SVG validation beyond "it has an `<svg>` root".
- Authentication.

## Technical approach

**Pattern registry** in `backend/lib/pattern_registry.py` (pure logic, no FastAPI):

```python
@dataclass
class PatternMeta:
    id: str
    name: str
    description: str
    piece_count: int
    svg_path: Path  # resolved at startup, not stored in response

@dataclass  
class PatternDetail(PatternMeta):
    svg: str  # loaded SVG content

def build_registry(patterns_dir: Path) -> dict[str, PatternMeta]: ...
def get_pattern(registry: dict[str, PatternMeta], pattern_id: str) -> PatternDetail: ...
```

Registry is built once at app startup and stored as a module-level singleton. `patterns_dir` points to `backend/lib/patterns/` which contains one subdirectory per pattern, each with a `meta.json` and an SVG file.

**Placeholder pattern** at `backend/lib/patterns/bodice-v1/`:
- `meta.json` — `{"id": "bodice-v1", "name": "Basic Fitted Bodice", "description": "...", "piece_count": 2, "svg_file": "bodice-v1.svg"}`
- `bodice-v1.svg` — a minimal valid SVG with two named groups (`front-bodice`, `back-bodice`), each containing a simple rectangle as a placeholder. Valid SVG. Will be replaced with the real pattern when Steph designs it.

**Routes** in `backend/routes/patterns.py` — two thin handlers calling into lib. Register under `/` prefix in `backend/main.py`.

## Dependencies

- No new external packages — uses `pathlib`, `json`, `dataclasses`, lxml (already present via pattern_ops).

## Testing approach

- **Unit tests** in `backend/tests/test_pattern_registry.py`:
  - `build_registry` with a temp patterns directory (use `tmp_path` pytest fixture)
  - `get_pattern` returns correct detail for known id
  - `get_pattern` raises `PatternNotFound` (subclass of `PatternError` from spec 01) for unknown id
- **Integration tests** via `TestClient`:
  - `GET /patterns` happy path
  - `GET /patterns/bodice-v1` returns svg field
  - `GET /patterns/nonexistent` returns 404 with detail message
- **SVG validity test**: parse the response `svg` field with lxml, assert root tag is `{...}svg`.

## Open questions

None.

## Notes for implementer

- The placeholder SVG just needs to be valid — two `<g id="front-bodice">` and `<g id="back-bodice">` groups each containing a `<rect>`. It will be replaced by Steph with the real pattern; don't spend time making it realistic.
- `PatternNotFound` should be a subclass of `PatternError` from `backend/lib/pattern_ops.py` to keep the error hierarchy consistent.
- The registry singleton: build it at module import time in `backend/lib/pattern_registry.py` using a relative path from the file's `__file__` location. Tests override it via `tmp_path`.
- Run cleanup checklist after implementation (see `.claude/commands/cleanup.md`).

## Implementation notes

### What was implemented

- `backend/lib/patterns/bodice-v1/meta.json` — placeholder pattern metadata.
- `backend/lib/patterns/bodice-v1/bodice-v1.svg` — minimal valid SVG with `<g id="front-bodice">` and `<g id="back-bodice">` each containing a `<rect>`.
- `backend/lib/pattern_registry.py` — pure-Python module with `PatternNotFound` (subclasses `PatternError`), `PatternMeta` dataclass, `PatternDetail` dataclass, `build_registry`, `get_pattern`, and module-level `REGISTRY` singleton built at import time from `backend/lib/patterns/`.
- `backend/routes/patterns.py` — thin FastAPI router with `GET /patterns` (returns list of `PatternMetaResponse`) and `GET /patterns/{pattern_id}` (returns `PatternDetailResponse` or 404). Uses Pydantic `model_validate` with `from_attributes=True` to convert dataclasses to response models.
- `backend/main.py` — registered `patterns_router` alongside existing routers.
- `backend/tests/test_pattern_registry.py` — 29 tests: 8 unit tests for `build_registry`, 7 for `get_pattern`, 6 integration tests for `GET /patterns`, 8 integration tests for `GET /patterns/{pattern_id}`.

### Deviations from spec

None. The implementation follows the spec exactly.

### Open questions for Steph

None. All acceptance criteria are met.

### New ADRs written

None required.

## Cleanup notes

- Checkboxes marked: 8 of 8
- Stray files removed: none found
- TODOs resolved: none found
- Linter/test result: PASS — 187 tests pass, ruff + black clean
- No items need Steph's attention before `/review`
