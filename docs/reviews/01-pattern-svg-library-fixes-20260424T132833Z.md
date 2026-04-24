# Review: 01-pattern-svg-library-fixes (2nd pass)

**Reviewed:** 2026-04-24T13:28:33Z
**Branch:** feat/01-pattern-svg-library-fixes
**Base:** main (46cc3b4)
**Head:** 138901c
**Spec:** docs/specs/01-pattern-svg-library.md
**Prior review:** docs/reviews/01-pattern-svg-library-fixes-20260424T131247Z.md (NEEDS CHANGES)

## Summary

**APPROVED** — Both prior-review items (B3 coverage gap, I4 M-subpath-start
bug) are fixed correctly. The new fix commit (138901c) is surgical, the new
tests assert exact expected coordinates (verified by hand against the stride
math and SVG spec), lint/format/tests all pass, and no new regressions were
introduced. Safe to merge.

## What's good

- **I4 fix (backend/lib/pattern_ops.py:288):** the guard
  `if upper == "M" and i == 0:` restricts the `start_x, start_y` update to the
  first pair of an M block, matching SVG spec (subsequent pairs are implicit
  lineto's). This is exactly the change suggested in the prior review.
- **B3 tests (tests/test_pattern_ops.py:1289-1365):** new
  `TestRelativeMultiPairCommands` class with three tests closes the coverage
  gap on the stride-based repetition loop:
  - `test_translate_relative_cubic`: exercises relative cubic (stride=3), the
    most common real-world use. Expected coordinates verified manually —
    `M 0,0 c 10,0 10,10 10,10` resolved absolute controls/endpoint are
    `(10,0), (10,10), (10,10)`; after translate +5,0 → `(15,0), (15,10),
    (15,10)`. Matches test assertions.
  - `test_translate_multi_pair_relative_lineto`: exercises multi-pair `m`
    continuation (stride=1, continuation pair path at line 275-276). Expected
    `(11,10), (16,15), (19,18)` verified against the code's per-repetition
    `rep_start` advance.
  - `test_multi_pair_M_subpath_start_not_overwritten`: regression test for
    I4. Before the fix, `start_x, start_y` would advance to `(10,10)` on the
    second pair of `M 0,0 10,10`, causing `Z` to return to the wrong anchor;
    test now asserts Z is preserved and the two coordinate pairs land at the
    expected (5,0) and (15,10). Good regression.
- **Coverage:** line 276 (the continuation-pair `rep_start` advance) is now
  hit. Pattern-ops coverage remains 98%; the nine remaining uncovered lines
  are all defensive guards (empty-d paths, missing attributes, odd trailing
  numbers).
- **Minimal commit scope:** diff is +84 test lines, 2 line change in
  `pattern_ops.py` (adding `and i == 0` to the subpath-start guard). No
  collateral edits.
- **Lint / format / tests:** `uv run pytest` → 221 passed; `ruff check .` →
  clean; `black --check .` → clean.

## Issues found

None blocking.

### Nit (carryover) — stale test-count in spec cleanup notes

**File:** `docs/specs/01-pattern-svg-library.md:142`

> Linter/test result: PASS — 95 pattern_ops tests, 215 backend tests total

After the 138901c commit the actual counts are 101 pattern_ops tests / 221
backend tests total. Not a blocker, not even a real issue — the cleanup note
was written one commit earlier. Fine to leave as-is or sweep during merge.

### Nit (N1, carried from prior review) — `_element_centroid` relative normalisation

**File:** `backend/lib/pattern_ops.py:_element_centroid`

Unchanged from prior review. Correctly scoped as out-of-scope pre-existing
behaviour (this branch does not touch `_element_centroid`). Follow-up work,
not a blocker for this PR.

### Nit (N2, carried from prior review) — `_extract_path_coords` fragile against `A`

**File:** `backend/tests/test_pattern_ops.py` (test helper)

Unchanged from prior review. Test helper only; no current test routes an arc
through it. Correctly scoped as a future-hardening nit, not a blocker.

## Acceptance-criterion coverage

No change from prior review's mapping. All 11 AC remain covered with
behaviourally meaningful tests:

| AC | Covered | Quality |
|----|---------|---------|
| AC1 load_pattern | TestLoadPattern | Good |
| AC2 render round-trip | TestRenderPattern | Good |
| AC3 translate_element | TestTranslateElement + new TestRelativeMultiPairCommands | Good |
| AC4 translate missing id | test_missing_id_raises_element_not_found | Good |
| AC5 rotate_element 90° | 3 known-pair tests + hypothesis round-trip + TestHVCommandRotation | Good |
| AC6 slash_line | TestSlashLine | Good |
| AC7 spread_at_line | test_elements_on_one_side_translate (exact coords) | Good |
| AC8 add_dart | test_dart_position_matches_input | Good |
| AC9 true_seam_length | polyline arc length + extend/shorten + zigzag | Good |
| AC10 purity | 6 tests (one per mutating op) | Good |
| AC11 coverage ≥ 90% | 98% reported | Good |

New for this review pass: relative multi-pair command paths — previously
un-exercised — now have explicit exact-coordinate tests.

## Verification I ran

- `git log main..feat/01-pattern-svg-library-fixes` → five commits, latest 138901c
  is the post-prior-review fix.
- `git diff 292ffc2^..138901c -- backend/lib/pattern_ops.py` → confirms the
  stride-loop refactor plus the single-line I4 guard fix.
- Manually traced expected coordinates for all three new tests against the
  stride-based `_transform_path_coords` loop; all match test assertions.
- Manually verified SVG spec: per §9.3.3 "After processing a moveto command,
  any subsequent coordinate pair(s) are treated as implicit lineto commands" —
  subpath start must not be updated on continuation pairs. Fix correct.
- `cd backend && uv run pytest --tb=short -q` → **221 passed** (101 in
  test_pattern_ops.py).
- `cd backend && uv run ruff check .` → clean.
- `cd backend && uv run black --check .` → clean.
- `cd backend && uv run pytest --cov=lib.pattern_ops --cov-report=term-missing
  tests/test_pattern_ops.py` → **98% coverage**; uncovered lines 294, 743,
  757, 824, 847, 866, 898-899, 910 — all defensive guards (empty `d`,
  malformed input, zero-length guards). Line 276 (B3 target) is now covered.
- Checked spec-09 file (`docs/specs/09-bezier-arc-length.md`) — legitimate
  new forward-looking spec, not scope creep into this branch.

## Questions for Steph

None. Ready to merge `feat/01-pattern-svg-library-fixes` → `main`.
