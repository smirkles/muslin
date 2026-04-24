# Spec: Pattern SVG Manipulation Library

**Spec ID:** 01-pattern-svg-library
**Status:** ready-for-implementation
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

- [ ] Given a valid SVG file, when `load_pattern` is called, then it returns a Pattern object with all `<path>` and `<g>` elements accessible by id.
- [ ] Given a Pattern, when `render_pattern` is called, then the output is a valid SVG string that parses back to an equivalent Pattern (round-trip stable).
- [ ] Given a Pattern with an element `foo`, when `translate_element(p, "foo", 10, 5)` is called, then the returned Pattern's `foo` element has all coordinates shifted by (10, 5). The original Pattern is unchanged.
- [ ] Given a Pattern, when `translate_element` is called with a non-existent id, then `ElementNotFound` is raised.
- [ ] Given a Pattern, when `rotate_element(p, "foo", 90, (0, 0))` is called, then the element is rotated 90° clockwise around the origin. Verify with at least 3 known rotation pairs.
- [ ] Given a Pattern, when `slash_line` is called, then a new `<line>` element with the given id is added. The rest of the pattern is unchanged.
- [ ] Given a Pattern with a slash line, when `spread_at_line(p, "slash1", 2.5, (1, 0))` is called, then the elements on one side of the slash are translated by (2.5, 0), and the slash line extends to cover the gap.
- [ ] Given a Pattern, when `add_dart` is called, then a dart-shaped polygon (triangle pointing toward the pattern interior) is added with the given id.
- [ ] Given a Pattern with seams A (length 10) and B (length 12), when `true_seam_length(p, "A", "B")` is called, then seam A's endpoint is extended to make its length 12 (within floating-point tolerance).
- [ ] All operations are pure — calling a function twice with identical inputs produces identical output Patterns.
- [ ] Test coverage ≥ 90% on the library module.

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
