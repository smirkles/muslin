# Spec: Pattern SVG Manipulation Library

**Spec ID:** 01-pattern-svg-library
**Status:** implemented
**Created:** 2026-04-23
**Depends on:** none

## What it does

A pure-Python library providing primitive geometric operations on sewing pattern SVGs. Every change to a pattern (grading, FBA, swayback, truing seams) is composed from these primitives. This is the foundation layer — if it's right, everything built on it inherits reproducibility. If it's wrong, every cascade silently breaks.

## User-facing behavior

No direct user interaction. The cascade engine, grading engine, and any future pattern transformation call into this library.

## Inputs and outputs

### Core type
`Pattern` — a parsed SVG document with addressable named elements. Loaded from an SVG file at project start, passed through operations, rendered back to SVG at end.

### Functions

All functions take a `Pattern` and parameters, return a new `Pattern` (immutable-style; caller gets a new object, source unchanged).

- `load_pattern(svg_path: Path) -> Pattern` — parse an SVG file.
- `render_pattern(pattern: Pattern) -> str` — serialize back to SVG string.
- `get_element(pattern: Pattern, element_id: str) -> Element` — retrieve named element.
- `translate_element(pattern: Pattern, element_id: str, dx: float, dy: float) -> Pattern` — move an element by (dx, dy).
- `rotate_element(pattern: Pattern, element_id: str, angle_deg: float, pivot: tuple[float, float]) -> Pattern` — rotate around a pivot point.
- `slash_line(pattern: Pattern, from_pt: tuple[float, float], to_pt: tuple[float, float], slash_id: str) -> Pattern` — add a slash line element; does not actually divide geometry yet.
- `spread_at_line(pattern: Pattern, slash_id: str, distance: float, direction: tuple[float, float]) -> Pattern` — take a slash line, actually divide the pattern across it and translate one side by `distance` in `direction`.
- `add_dart(pattern: Pattern, position: tuple[float, float], width: float, length: float, angle_deg: float, dart_id: str) -> Pattern` — add a dart at specified position.
- `true_seam_length(pattern: Pattern, seam_a_id: str, seam_b_id: str) -> Pattern` — adjust `seam_a` to match the length of `seam_b` by extending/contracting at its endpoint.

### Errors
- `PatternError` — base exception class.
- `ElementNotFound` — when `element_id` doesn't exist in the pattern.
- `GeometryError` — when an operation can't be geometrically performed (e.g. spread at a slash line that isn't in the pattern).

## Acceptance criteria

- [x] Given a valid SVG file, when `load_pattern` is called, then it returns a Pattern object with all `<path>` and `<g>` elements accessible by id.
- [x] Given a Pattern, when `render_pattern` is called, then the output is a valid SVG string that parses back to an equivalent Pattern (round-trip stable).
- [x] Given a Pattern with an element `foo`, when `translate_element(p, "foo", 10, 5)` is called, then the returned Pattern's `foo` element has all coordinates shifted by (10, 5). The original Pattern is unchanged.
- [x] Given a Pattern, when `translate_element` is called with a non-existent id, then `ElementNotFound` is raised.
- [x] Given a Pattern, when `rotate_element(p, "foo", 90, (0, 0))` is called, then the element is rotated 90° clockwise around the origin. Verify with at least 3 known rotation pairs.
- [x] Given a Pattern, when `slash_line` is called, then a new `<line>` element with the given id is added. The rest of the pattern is unchanged.
- [x] Given a Pattern with a slash line, when `spread_at_line(p, "slash1", 2.5, (1, 0))` is called, then the elements on one side of the slash are translated by (2.5, 0), and the slash line extends to cover the gap.
- [x] Given a Pattern, when `add_dart` is called, then a dart-shaped polygon (triangle pointing toward the pattern interior) is added with the given id.
- [x] Given a Pattern with seams A (length 10) and B (length 12), when `true_seam_length(p, "A", "B")` is called, then seam A's endpoint is extended to make its length 12 (within floating-point tolerance).
- [x] All operations are pure — calling a function twice with identical inputs produces identical output Patterns.
- [x] Test coverage ≥ 90% on the library module (achieved: 98%).

## Out of scope

- Actual pattern grading logic (that's a separate feature, 04-cascade-* specs).
- Rendering patterns to anything other than SVG (no PDF, no DXF, no physical dimensions).
- Pattern validation (checking that a "pattern" is actually a sewable shape).
- Handling of SVG features beyond `<path>`, `<polygon>`, `<line>`, `<g>`, `<text>` — no embedded images, no gradients, no filters.
- Curve manipulation (bezier adjustment). For V1 we approximate curves as polylines. Flag as future work.

## Technical approach

- Parse SVG with `lxml` (robust, well-known).
- Represent `Pattern` as a thin wrapper around the parsed `ElementTree`, with an internal `_id_index: dict[str, Element]` for fast lookup.
- Coordinate transformations use `numpy` for matrix math.
- All functions return new Patterns — implemented via deep copy. Performance is fine since patterns are small (dozens of elements).
- Keep coordinate system consistent: SVG default (y increases downward), document this loudly in code.

## Dependencies

- `lxml` for SVG parsing
- `numpy` for coordinate math
- `pytest` for testing
- No dependency on FastAPI or any web framework — this library is pure logic.

## Testing approach

- **Unit tests** in `backend/tests/test_pattern_ops.py`.
- Use small hand-crafted SVG fixtures in `backend/tests/fixtures/patterns/` (a simple triangle, a rectangle, a shape with a named dart).
- Test each function with:
  - Happy path (valid input, expected output).
  - Edge cases (zero translation, 360° rotation, missing elements).
  - Error cases (invalid input raises the right exception).
- **Golden file tests** for render_pattern round-trip: load, render, re-parse, compare trees.
- **Property-based tests** (hypothesis) for rotation: rotating by X then -X should return to original within tolerance.

## Open questions

None. Ready for implementation.

## Notes for implementer

- Coordinates in SVG use (x, y) with y increasing downward. Easy to flip if you're thinking mathematically. Be explicit in docstrings.
- For `rotate_element`, use a 2x2 rotation matrix applied to every coordinate in every `<path>`'s `d` attribute. This means parsing path commands; use `svg.path` or similar if lxml is too low-level. Check first if lxml alone suffices.
- `spread_at_line` is the trickiest one. Don't overthink it for V1 — we can assume slash lines are straight and that the pattern is topologically simple. Document assumptions in code.
- Immutability matters for reproducibility. Copy-on-write is the cleanest pattern.

## Implementation notes

### What was implemented

Single-file module at `backend/lib/pattern_ops.py` (370 statements) implementing all functions from the spec:

- `Pattern` class: thin wrapper around lxml `ElementTree` with `_id_index: dict[str, Element]` for O(1) lookup. `_deep_copy()` uses `copy.deepcopy` on the root element for true immutability.
- `load_pattern` / `render_pattern` / `get_element`: straightforward lxml wrappers.
- `translate_element` / `rotate_element`: dispatch on element tag (`<path>`, `<polygon>`, `<line>`, `<text>`). Path `d` attribute parsing handles M/L/H/V/C/S/Q/T/A/Z commands.
- `slash_line`: appends a `<line>` to the SVG root with namespace awareness.
- `spread_at_line`: classifies elements by centroid signed distance from the slash line's perpendicular normal. Elements on the right side (or on the line) are translated. The slash line's x2/y2 is extended by the spread distance.
- `add_dart`: builds an isosceles triangle polygon from tip, direction angle, width, and length.
- `true_seam_length`: finds Euclidean length of seam B (start→end), then rescales seam A's endpoint along its own direction vector to match.

Three fixture SVGs created in `backend/tests/fixtures/patterns/`: `triangle.svg`, `rectangle.svg`, `with_dart.svg`.

**Test suite:** 83 tests in `backend/tests/test_pattern_ops.py` covering all 11 acceptance criteria. Hypothesis property-based test for rotation round-trip (50 examples). 98% coverage on `lib/pattern_ops.py`.

### Deviations from spec

- lxml was sufficient for all path parsing — no `svg.path` library needed. A custom tokenizer (`_TOKEN_RE`) handles all SVG path command formats.
- `spread_at_line` classifies elements by centroid, not by geometric intersection. Elements crossing the slash line are moved with the right side. This is documented in the docstring as a V1 assumption.
- `true_seam_length` measures length as the Euclidean distance from the *first* to the *last* coordinate pair (not the sum of segment lengths). This matches the spec's example (straight seams) and is documented.
- `translate_element` on a `<g>` element does nothing (no-op) — the spec doesn't specify group translation behavior; moving individual children is more predictable.

### Open questions for Steph

- Should `spread_at_line` handle elements that straddle the slash line differently? Currently they move with the right side (conservative). For real FBA use cases, straddling elements might need to be split.
- `true_seam_length` uses start→end Euclidean distance. For curved seams (future work), this will be wrong — should we add a warning/flag for curved paths?
- `translate_element` on `<g>` is currently a no-op. Should it recurse into children instead?

### Cleanup notes (initial — 2026-04-23)

- All 11 spec acceptance criteria are checked off above.
- No TODOs left in source code (future-work items are in docstrings, not inline TODOs).
- Ruff + black both pass clean.
- All 99 backend tests pass (83 new + 16 pre-existing).
- No new ADRs needed — all decisions follow existing patterns or are self-evident V1 simplifications documented in code.

### Cleanup notes (post-review fix — 2026-04-24)

- Checkboxes marked: 11 of 11 (all passing).
- Stray files: none introduced by this fix. Untracked `docs/reviews/` files are review artifacts (expected). `docs/specs/09-*.md` is a new spec, not a stray.
- TODOs / future-work flags found: 3 (bezier distortion under rotation at line 31 and 203; `spread_at_line` straddling-element caveat at line 565). All are docstring annotations, not inline TODOs — no action needed.
- Linter/test result: PASS — 95 pattern_ops tests, 215 backend tests total; `ruff check` clean; `black --check` clean.
- No `.env`, secrets, or credential files staged or untracked.
- `pyproject.toml` and `uv.lock` unchanged — no dependency changes.
- Items needing Steph's attention: none introduced by this fix. The three open questions from the initial cleanup notes (straddling elements, curved seams, `<g>` translation) remain open and unchanged.
