# Spec: Bezier Arc Length for Pattern Seam Measurement

**Spec ID:** 09-bezier-arc-length
**Status:** ready-for-implementation
**Created:** 2026-04-24
**Depends on:** 01-pattern-svg-library

## What it does

Upgrades `true_seam_length` (and the internal `_path_length` helper) to measure curved seam paths correctly by approximating Bezier curves via adaptive chord subdivision rather than straight-line distances between on-curve endpoints. Real sewing patterns use cubic Bezier curves (C/S commands) on every armhole, neckline, and princess seam; the current polyline approximation (connecting only the declared anchor endpoints) underestimates these lengths. This fix is needed before any pattern grading or FBA that touches curved seams can be trusted.

## User-facing behavior

No direct user interaction. Calling code sees `true_seam_length(pattern, seam_a_id, seam_b_id)` return a corrected Pattern where seam A's arc length matches seam B's arc length to within floating-point tolerance. The only observable change is correctness: a curved seam that was previously "extended" by an incorrect amount will now be extended by the right amount.

## Inputs and outputs

### Inputs

`true_seam_length(pattern: Pattern, seam_a_id: str, seam_b_id: str) -> Pattern` — unchanged signature. Internal `_path_length(el)` and `_path_anchor_points(d)` are the implementation targets.

### Outputs

Same as before: a new `Pattern` where `seam_a`'s arc length equals `seam_b`'s arc length.

### Errors

- `GeometryError` — if a path has fewer than 2 points (unchanged).
- No new error cases.

## Acceptance criteria

- [ ] Given a cubic Bezier path `M 0,0 C 0,100 100,100 100,0` (quarter-ellipse approximation, true arc length ≈ 157.08), when `_path_length` is called, then the result is within 1% of 157.08.
- [ ] Given two paths where seam B is a cubic Bezier of known arc length L, when `true_seam_length(p, seam_a_id, seam_b_id)` is called, then the resulting seam A has arc length within 0.5 mm (or 0.5 SVG units) of L.
- [ ] Given a straight-line path (M/L only), when `_path_length` is called, the result is identical to the pre-existing polyline calculation (no regression).
- [ ] Given a path with S (smooth cubic) commands, when `_path_length` is called, the result is within 1% of the true arc length (verified against a reference value computed by numerical integration or a trusted library).
- [ ] Given a path with Q (quadratic Bezier) commands, when `_path_length` is called, the result is within 1% of the true arc length.
- [ ] All existing `TestTrueSeamLengthPolyline` tests continue to pass (no regression on M/L paths).

## Out of scope

- A (arc) command length measurement — treat A segments as straight chords for now; flag in docstring. Full elliptical arc length requires numerical integration beyond V1 scope.
- T (smooth quadratic) command measurement — treat as straight chord; flag in docstring.
- UI exposure of measured seam lengths.
- Tolerance configuration — hardcode 32 subdivision steps (sufficient for <0.1% error on typical pattern curves).

## Technical approach

Replace the naive "collect anchor endpoints, sum Euclidean distances" approach in `_path_anchor_points` / `_path_length` with per-segment arc length calculation:

- **M, L, H, V segments**: straight-line Euclidean distance, unchanged.
- **C (cubic Bezier)**: subdivide using de Casteljau to a fixed depth (e.g. 5 levels = 32 segments) and sum chord lengths. Alternatively use the analytic approximation from Gravesen (1993) — adaptive subdivision is simpler to implement and verify.
- **S (smooth cubic)**: compute the implied first control point from the previous command's reflected endpoint, then treat as C.
- **Q (quadratic Bezier)**: same subdivision approach, 5 levels.
- **A (arc)**: straight chord from start to end (documented limitation).
- **T (smooth quadratic)**: straight chord (documented limitation).

`_adjust_path_endpoint_length` already works in arc-length space (it accumulates distances segment by segment). Once `_path_length` is correct, the endpoint adjustment logic inherits correctness for the common case. Only the arc-length-accumulation in `_adjust_path_endpoint_length` itself needs updating to use the per-segment Bezier arc length rather than the straight-chord distance for C/S/Q segments.

Pen-position tracking is already done (introduced in the B1/B2 fix). Reuse that infrastructure.

## Dependencies

- `numpy` — already a dependency, sufficient for de Casteljau arithmetic.
- No new external libraries needed.
- Spec 01 (`01-pattern-svg-library`) must be implemented — it is.

## Testing approach

- **Unit tests** in `backend/tests/test_pattern_ops.py`, new class `TestBezierArcLength`.
- Reference values for cubic Bezier arc lengths can be computed via scipy `integrate.quad` on the speed function, or taken from published tables for standard curves.
- Test the quarter-ellipse approximation `M 0,0 C 0,100 100,100 100,0` — a well-known case with reference ≈ 157.08.
- Test that regression suite (`TestTrueSeamLengthPolyline`) still passes.
- No hypothesis property tests needed here — deterministic geometry, fixed fixtures suffice.

## Open questions

None. Ready for implementation.

## Notes for implementer

- The de Casteljau subdivision at depth 5 gives 32 sub-segments. For a typical sewing pattern curve (say, a 300 SVG-unit armhole), this yields sub-chords of ~9 units, which is well under 0.1% error. Depth 6 (64 segments) is available if tighter tolerance is needed.
- `_path_anchor_points` was introduced as an internal helper in the polyline fix. You may replace it entirely or extend it to return richer per-segment data. Keep the function private.
- The pen-position tracking in `_transform_path_coords` is the authoritative place where relative commands are resolved. `_path_length` should call `_transform_path_coords(d, lambda x, y: (x, y))` first to normalize the path to absolute uppercase commands before measuring. This is already done in the current implementation.
- `_adjust_path_endpoint_length` accumulates arc length segment by segment when shortening. Each segment's contribution needs to use the Bezier chord sum (not the straight-chord) for C/S/Q segments. The loop structure already supports this — just replace `np.linalg.norm(...)` with the appropriate segment length function.
