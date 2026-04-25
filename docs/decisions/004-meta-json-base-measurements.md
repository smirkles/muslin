# ADR 004: Extend meta.json with Base Measurements

**Date:** 2026-04-25
**Status:** Accepted

## Context

Spec 10 (pattern grading) needs to know the base body measurements that a pattern is drafted for (bust, waist, hip, back_length in cm). Without these, the grading algorithm cannot compute the ratio between the base size and the user's measurements.

The registry already reads `meta.json` from each pattern directory. The metadata is already loaded as `PatternMeta` and exposed through the API. Adding base measurements here avoids a separate file format.

## Decision

Add four optional fields to `meta.json` for each pattern:
- `base_bust_cm`
- `base_waist_cm`
- `base_hip_cm`
- `base_back_length_cm`

Correspondingly, update:
1. `PatternMeta` dataclass — add the four fields (type `float | None` to allow existing patterns that don't have them yet to still load without error, but grading will require non-None values).
2. `build_registry` — read and populate the four fields from `meta.json` using `.get()` with `None` as default.
3. `bodice-v1/meta.json` — add representative base measurements: `bust=92, waist=74, hip=100, back_length=40` (UK/AU size 12 standard block).

`PatternDetail` inherits from `PatternMeta` so it automatically gains the four fields.

Route response schemas (`PatternMetaResponse`, `PatternDetailResponse`) do not expose base measurements by default — they are implementation-internal to grading. This avoids leaking sizing details in the pattern catalogue API. The grading route reads them directly from the registry.

## Consequences

### Positive
- Patterns without base measurements still load cleanly (fields are `None`).
- Base measurements are version-controlled alongside the SVG and other metadata.
- No new file format or database table required.
- Grading can be applied to any future pattern simply by adding four lines to its `meta.json`.

### Negative
- Grading will fail at runtime (with a clear 500 error) for patterns that have no base measurements in their `meta.json`. Acceptable for V1; future patterns will always include these fields.
- `PatternMeta` gains four fields that most of the codebase ignores. Minor leakage of grading concerns into the core registry type.

## Alternatives considered

- **Separate `grading_meta.json` per pattern:** extra file, more I/O, no clear benefit for V1. Rejected.
- **Hardcode base measurements in grading.py:** makes it impossible to add a second pattern without a code change. Rejected.
- **Store in a database:** out of scope for a hackathon project with an in-memory store. Rejected.

## References

- `docs/specs/10-pattern-grading.md`
- `backend/lib/pattern_registry.py` — `PatternMeta`, `build_registry`
- `backend/lib/patterns/bodice-v1/meta.json`
