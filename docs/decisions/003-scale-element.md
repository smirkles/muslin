# ADR 003: Add scale_element() to pattern_ops

**Date:** 2026-04-25
**Status:** Accepted

## Context

Spec 10 (pattern grading) requires scaling individual pattern pieces by a horizontal and/or vertical factor around a pivot point, so that bodice pieces grow by `user_bust / base_bust` and all pieces grow vertically by `user_back_length / base_back_length`. This is a new geometric primitive not currently in `pattern_ops.py`.

The project rule is: "All SVG manipulation goes through `backend/lib/pattern_ops/`." The grading logic in `backend/lib/grading.py` must therefore call a function in pattern_ops rather than directly mutate SVG elements.

## Decision

Add a public function `scale_element(pattern, element_id, sx, sy, pivot)` to `backend/lib/pattern_ops.py`, alongside the existing `translate_element` and `rotate_element` functions.

Implementation:
- Deep-copy the pattern first (pure function — no mutation).
- Apply coordinate transform `(pivot_x + (x - pivot_x) * sx, pivot_y + (y - pivot_y) * sy)` to every descendant element.
- Reuse `_transform_path_coords` with a scale lambda for `<path>` elements (consistent with the existing translate and rotate approach).
- Recurse into `<g>` elements the same way `_rotate_element` does — every descendant uses the same pivot, not its own bbox centre.
- Support `<path>`, `<polygon>`, `<line>`, `<text>` exactly as the other element transforms do.
- Bezier control points scale identically to anchor points (V1 convention, already documented at the top of the module).

A private helper `_element_bbox(el)` is also added to compute the bounding box of any element or `<g>` subtree, needed to compute the pivot (bounding-box centre). This mirrors `_element_centroid` but returns min/max rather than a mean.

## Consequences

### Positive
- All SVG geometry stays in one module; downstream callers (grading, future cascade steps) never touch lxml directly.
- The scale lambda reuses the exact same path-coordinate transform machinery as translate and rotate, so all coordinate types (path d, polygon points, line endpoints, text x/y) are handled consistently.
- Bounding-box helper is useful for future operations (e.g. auto-layout, cascade visualisation).

### Negative
- `pattern_ops.py` grows. If we add many more primitives it may need splitting into a sub-package.
- H/V path commands are promoted to L (already done by the translate/rotate paths), which slightly increases SVG file size. Accepted: V1 does not optimise output file size.

## Alternatives considered

- **Apply scaling via SVG `transform` attribute:** simpler to write, but downstream code (including true_seam_length, FBA, swayback) reads raw coordinates — a `transform` attribute would silently break those operations. Rejected.
- **Implement scaling inside grading.py using lxml directly:** violates the "all SVG manipulation through pattern_ops" rule. Rejected.
- **Per-child pivot (bbox of each descendant independently):** would cause pieces to drift since each child would scale around its own centre. Incorrect for garment grading. Rejected.

## References

- `docs/specs/10-pattern-grading.md`
- `backend/lib/pattern_ops.py` — existing `translate_element`, `rotate_element` for pattern
