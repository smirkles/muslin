# Review: 09-bezier-arc-length

**Reviewer:** fresh-context review agent
**Reviewed at:** 2026-04-25T10:20:51Z
**Branch:** `feat/09-bezier-arc-length`

## Verdict: NEEDS CHANGES

---

## Acceptance criteria

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| AC1 | `_path_length` for `M 0,0 C 0,100 100,100 100,0` within 1% of 157.08 | ⚠️ partial | Implementation gives ~200.0, not ~157.08. 157.08 is wrong in the spec. Test uses self-consistent n=1000 reference (~200.0) and passes 1% threshold against that. |
| AC2 | `true_seam_length(p, seam_a, bezier_seam_b)` → seam A within 0.5 SVG units | ✅ passing | Test passes; seam-a (L path) extended to match seam-b (C path). |
| AC3 | Straight-line path: result identical to polyline calculation | ✅ passing | Tested with `M 0,0 L 30,40 L 60,0`, result matches expected 100.0. |
| AC4 | S command path within 1% of true arc length | ✅ passing | Tests both the degenerate case (S with no prior C → equals explicit C) and that S arc exceeds chord. |
| AC5 | Q command path within 1% of high-precision reference | ✅ passing | Tested against n=1000 self-consistent reference. |
| AC6 | `TestTrueSeamLengthPolyline` regression suite passes | ✅ passing | All 3 existing tests pass. |

---

## Findings

### Blockers

None. All tests pass, lint is clean, and the implementation is functionally correct.

### Required changes

**Misleading commit message for core implementation (`035f3fd`)**

The commit titled `chore: black-format pattern_ops.py (pre-existing)` is mislabeled. It contains 161 lines of new implementation code — the Bezier arc length helpers (`_cubic_bezier_arc_length`, `_quadratic_bezier_arc_length`, `_path_segment_lengths`) and updated `_path_length` / `_adjust_path_endpoint_length`. The subsequent commit titled `feat: implement 09-bezier-arc-length` contains only tests.

This creates a misleading git history: a reviewer looking at the "feat:" commit sees only test additions and might conclude the implementation was done elsewhere or is missing. It also violates the project's tests-before-implementation convention (spec says "Write failing tests from the spec first, then make them pass" — CLAUDE.md) since the implementation commit precedes the test commit by commit order.

This does not break any tests and the code is functionally correct, but the commit attribution is wrong and the history is misleading. **This is a required change for history legibility**, but the branch already exists in its current form. Steph should decide whether to rebase-and-reword before merge or accept the misleading history as-is.

**AC1: Spec reference value is incorrect**

`backend/docs/specs/09-bezier-arc-length.md`, line 33:
> Given a cubic Bezier path `M 0,0 C 0,100 100,100 100,0` (quarter-ellipse approximation, true arc length ≈ 157.08)

157.08 (= π·50) is the arc length of a true quarter-circle with radius 50. The curve `M 0,0 C 0,100 100,100 100,0` is NOT a quarter-circle approximation; its true arc length is ~200.0. The implementer correctly identified this discrepancy in the test comment and pivoted to a self-consistent n=1000 reference. However:

1. The spec is factually wrong and should be corrected (even if this is after implementation).
2. The AC1 test does NOT test that the result is "within 1% of 157.08" as stated — it tests against ~200.0. If anyone re-runs the test expecting AC1 to verify 157.08, they will be confused.

The implementation is correct. The spec and/or test comment needs a clarifying note. Per reviewer rules, I cannot modify the spec — flagging for Steph.

### Suggestions (non-blocking)

**Dead code: `_path_anchor_points` is now unreachable**

`backend/lib/pattern_ops.py`, line 1106: `_path_anchor_points` is defined but no longer called by any production code (both `_path_length` and `_adjust_path_endpoint_length` now use `_path_segment_lengths`). Its docstring also incorrectly references "spec-10 handles full Bezier arc length" when spec-09 now does this.

The function should either be removed or its docstring updated to reflect its obsolete status. Leaving dead code with an incorrect docstring risks confusing future readers into thinking the chord-length approximation is still in use.

**`_path_anchor_points` docstring references spec-10 incorrectly**

Line 1111: `"chord-length lower-bound approximation for curved segments (spec-10 handles full Bezier arc length)."` — spec-09 (this spec) has now delivered the Bezier arc length. The docstring should say spec-09, or the function should be deleted.

**`noqa: E402` on import line**

`backend/tests/test_pattern_ops.py`, line 29: `# noqa: E402` is suppressing an "import not at top of file" warning. The justification comment is only on line 34 (`_path_length, # noqa: F401`). The E402 on line 29 should also have a justification comment.

**AC4 only tests degenerate S (no prior C)**

The test `test_s_command_matches_equivalent_c_command` tests S with no prior C command, where the implied c1 equals the pen position (degenerate case). The spec requires testing S "within 1% of true arc length" generally. A second test covering S after a C (where the reflected c1 is non-trivial) would better validate the reflection logic. The `test_s_command_exceeds_chord_length` test does use `C ... S` in sequence, which exercises the reflection path, but it only checks `length > chord` rather than accuracy to a reference value.

---

## Test quality

The 8 tests in `TestBezierArcLength` are well-structured and directly map to the acceptance criteria. Specific observations:

- **AC1 test** correctly handles the spec's wrong reference value by computing a self-consistent reference, and the comment explains the discrepancy. This is good defensive testing, though the spec should be corrected.
- **AC2 test** constrains seam-a to be a straight line, which makes the Euclidean distance check valid. If seam-a were itself a Bezier, `_extract_path_coords` would extract control points as coordinate pairs, giving wrong results. This is acceptable for the current test fixture but brittle if fixtures change.
- **AC3 test** is exact and correct.
- **AC4 test**: the "matches equivalent C" test is tight (tolerance 0.01 SVG units, much tighter than 1%). The "exceeds chord" test provides weaker coverage for the reflection case.
- **AC5 test** is correct and well-constructed.
- **Regression suite (AC6)** passes without modification.

No tests are trivial (no `assert result is not None`-type assertions). Tests test behavior, not implementation internals, except for the direct `_path_length` calls which are intentional and justified.

---

## Convention checks

| Check | Result |
|-------|--------|
| Hardcoded prompts in code | Not applicable (no prompts involved) |
| SVG manipulation outside `pattern_ops/` | None found |
| FastAPI imports inside `lib/` | None found |
| Type hints on all public functions | All present |
| `any` types in TypeScript | Not applicable |
| Lint (ruff) | Passes |
| Formatting (black) | Passes |
| Full test suite | 539 passed, 1 skipped |
| Suppressed warnings without justification | `noqa: E402` on line 29 lacks inline justification comment (minor) |

---

## Questions for Steph

1. **AC1 spec reference value**: The spec says 157.08 for `M 0,0 C 0,100 100,100 100,0`; the true value is ~200.0. The test correctly uses ~200.0. Should the spec be updated to correct the reference, or should the spec be left as written (since it's the source of truth)?

2. **Commit history**: The core implementation is in a commit labeled `chore: black-format`. Do you want to rebase/reword before merging so the history accurately reflects that commit 035f3fd is the feature implementation?

3. **Dead code**: `_path_anchor_points` is now unreachable in the feature branch. Remove it now, or leave for a later cleanup commit?
