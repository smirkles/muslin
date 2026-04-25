# Review: 01-pattern-svg-library-fixes

**Reviewed:** 2026-04-24T13:12:47Z
**Branch:** feat/01-pattern-svg-library-fixes
**Base:** main (46cc3b4)
**Head:** 5062246
**Spec:** docs/specs/01-pattern-svg-library.md

## Summary

**NEEDS CHANGES** — The fixes for B1 and B2 are structurally correct and the
reworked tests for I1, I2, I3 are behaviourally meaningful. However, the
implementation restructuring for B1 specifically introduced a new code path for
multi-pair relative commands (C, S, Q, and continuation pairs of M/L) that is
not exercised by any test. Line 276 of `backend/lib/pattern_ops.py` — the
`rep_start_x, rep_start_y = cur_x, cur_y` advance for a new repetition within
one command letter — is uncovered by the suite. Given that B1 existed precisely
because the old code mis-handled relative offsets, shipping with the multi-pair
relative path un-tested leaves the cascade-reproducibility guarantee on
uncertain ground.

## What's good

- **B2 (H/V rotation promotion):** correct and well-tested. Rotation matrix math
  confirmed for 90° CW in SVG y-down space. Three tests (origin H, origin V,
  non-origin pivot H) cover the promoted-to-L behaviour with exact coordinate
  assertions. Matches spec's "must be rotated around both axes".
- **B1 (relative single-pair `m`/`l`):** correctly resolves the pen position
  before applying the transform. Output normalises to uppercase absolute
  commands. The rotation case around a non-origin pivot (`test_rotate_relative_path_around_non_origin_pivot`)
  catches the regression that made this a blocker.
- **I1 (spread_at_line AC7):** new test creates explicit left/right-of-slash
  paths and asserts right-path shifts by (10, 0) while left-path is unchanged —
  signed-distance normal math verified by inspection (vertical slash → normal
  (1, 0); centroid 225 is right-side, centroid 50 is left-side).
- **I2 (add_dart AC8):** now parses polygon vertices and asserts
  `vertices[0] == position` to sub-1e-4 tolerance. Tests the behaviour, not the
  format.
- **I3 (H/V translate):** replaced substring `"60" in d` assertions with
  `_extract_path_coords` parsing and exact-value comparisons across all
  endpoints. Will catch a regression where only the shifted axis is present in
  the output string.
- **Arc-length fix (`true_seam_length`):** `_path_length` now sums Euclidean
  segment distances over anchor points. `_adjust_path_endpoint_length`
  correctly handles both extend (advance last segment) and shorten (interpolate
  on segment that crosses target). Zigzag tests (`M 0,0 L 3,4 L 0,8`, polyline
  length 10 vs start-to-end 8) cover the previously broken case.
- **Purity regression coverage:** new `test_spread_at_line_is_pure` and
  `test_true_seam_length_is_pure` close an AC10 gap that was not explicit
  before.
- **Type hygiene:** `typing.Any` replaced with
  `collections.abc.Callable[[float, float], tuple[float, float]]` for
  `_make_rotate_fn` and the `_transform_path_coords` `fn` parameter. No new
  `Any` introduced.
- **Lint / types / tests:** `ruff check .` clean, `black --check .` clean,
  `uv run pytest` = 218 passed. Coverage on `lib/pattern_ops.py` = 98%.

## Issues found

### Blocker (B3) — B1 coverage gap on multi-pair relative commands

**File:** `backend/lib/pattern_ops.py:271-289` (and corresponding tests)

The restructured loop (stride-based pair iteration) is the heart of the B1
fix. It adds specific handling for `C` (stride=3), `S` (stride=2), `Q` (stride=2),
and for *continuation pairs within a single command letter* (e.g.,
`l 5,5 3,3` where both pairs share the same `l` letter). None of these paths
are tested:

- No test exercises a relative cubic Bezier (`c x1,y1 x2,y2 x3,y3 …`). This
  is the single most common relative command in real patterns (every armhole
  curve). The docstring on line 200-201 explicitly claims correctness for
  multi-pair C/S/Q, but the behaviour is unverified.
- No test exercises multi-pair `l` or `m` continuation (e.g., `m 10,10 5,5 3,3`).
- Coverage report confirms line 276 (the `if pair_in_rep == 0 and i > 0:`
  branch that fires only on continuation pairs) is not hit by any test.

**Why this is a blocker, not an important:** The branch exists specifically to
fix relative-command correctness. The claim "relative SVG path commands are now
resolved to absolute coordinates before any transform is applied" is the spec
adherence check for B1, and it currently cannot be verified for the most
common real-world case. Per CLAUDE.md: *"All SVG manipulation goes through
`backend/lib/pattern_ops/`. Do not manipulate SVG elsewhere. This is the only
way cascade reproducibility holds."* A relative cubic that silently
mis-transforms under rotation would break cascade reproducibility for every
curved seam.

**Suggested fix (two tests, one class):**

```python
class TestRelativeMultiPairCommands:
    def test_translate_relative_cubic(self) -> None:
        # M 0,0 c 10,0 10,10 10,10 → abs endpoints of control/end: (10,0),(10,10),(10,10)
        # Translate (+5, 0) → (15,0),(15,10),(15,10)
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><path id="p" d="M 0,0 c 10,0 10,10 10,10"/></svg>'
        p = load_pattern_from_string(svg)
        p2 = translate_element(p, "p", 5.0, 0.0)
        # Parse C coords out of new d, assert each of the three pairs.

    def test_translate_multi_pair_relative_lineto(self) -> None:
        # m 10,10 5,5 3,3 → abs endpoints (10,10), (15,15), (18,18)
        # Translate (+1, 0) → (11,10), (16,15), (19,18)
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><path id="p" d="m 10,10 5,5 3,3"/></svg>'
        p = load_pattern_from_string(svg)
        p2 = translate_element(p, "p", 1.0, 0.0)
        coords = _extract_path_coords(get_element(p2, "p").get("d"))
        assert coords == [(11.0, 10.0), (16.0, 15.0), (19.0, 18.0)]  # with tolerance
```

### Important (I4) — `start_x`/`start_y` updated on every M-block pair

**File:** `backend/lib/pattern_ops.py:284-287`

```python
if pair_in_rep == stride - 1:
    cur_x, cur_y = abs_x, abs_y
    if upper == "M":
        start_x, start_y = cur_x, cur_y
```

Per SVG spec, only the *first* pair of an `M`/`m` block defines the subpath
start. Subsequent pairs in the same command are implicit lineto's and must
*not* reset the subpath start. This code updates `start_x, start_y` on every
pair because `M` has stride=1 (so `pair_in_rep == stride-1` is true for every
pair).

Observable consequences: a path like `M 0,0 10,10 Z l 5,5` would return to
`(10,10)` instead of `(0,0)` on `Z`, so the relative `l 5,5` that follows would
be placed at `(15,15)` instead of `(5,5)`.

This bug is latent — no current test hits it — but it is newly introduced by
this branch's restructuring (the previous code didn't track subpath starts at
all). Not a blocker because cascade callers won't typically emit pathological
multi-pair M blocks, but it should be fixed alongside the missing B1 tests.

**Suggested fix:** Track subpath start on the *first* pair only.

```python
if pair_in_rep == stride - 1:
    cur_x, cur_y = abs_x, abs_y
    if upper == "M" and i == 0:  # only on the first pair of an M block
        start_x, start_y = cur_x, cur_y
```

(Alternatively, move the subpath-start assignment to a separate `first_pair`
flag.)

### Nit (N1) — `_element_centroid` does not normalise relative commands

**File:** `backend/lib/pattern_ops.py:730-775`

`_element_centroid` iterates `_parse_path_d(d)` directly and treats every
coordinate pair as absolute, which is wrong for paths that use relative
commands. For `m 10,10 l 5,5`, the computed centroid is `(7.5, 7.5)` — the
mean of `(10,10)` and `(5,5)` — when the actual absolute points are `(10,10)`
and `(15,15)`, centroid `(12.5, 12.5)`. This could cause `spread_at_line` to
mis-classify relatively-coded elements.

**Pre-existing** — the diff does not touch this function, so it is out of scope
for this branch. Flagging as a follow-up: the cleanest fix is one line —
`d_norm = _transform_path_coords(d, lambda x, y: (x, y))` then parse
`d_norm` — mirroring the fix already applied to `_path_length`. Worth a tiny
spec addendum or a separate ticket rather than folding into this branch.

### Nit (N2) — `_extract_path_coords` test helper is fragile against `A` output

**File:** `backend/tests/test_pattern_ops.py:69-81`

The regex only strips `[MLZCzmlc]` and doesn't handle `A` or the flags within
an arc. If a future test routes an arc path through this helper, it will raise
`ValueError` on the letter `"A"`. Low priority — no current test does this —
but a brief comment on the helper or a more permissive regex would prevent a
surprise in future work.

## Test coverage gaps

Mapping spec acceptance criteria to test coverage:

| AC | Covered by | Quality |
|----|-----------|---------|
| AC1 load_pattern | `TestLoadPattern` (7 tests) | Good |
| AC2 render_pattern round-trip | `TestRenderPattern` (6 tests) | Good |
| AC3 translate_element | `TestTranslateElement` (11 tests, inc. H/V/polygon/line/text) | Good |
| AC4 translate missing id | `test_missing_id_raises_element_not_found` | Good |
| AC5 rotate_element 90° CW | three known-pair tests + property-based round-trip | Good |
| AC6 slash_line | `TestSlashLine` (5 tests) | Good |
| AC7 spread_at_line | `test_elements_on_one_side_translate` (now exact coord assertions) | Good after I1 fix |
| AC8 add_dart | `test_dart_position_matches_input` (tip-at-pos exact assertion) | Good after I2 fix |
| AC9 true_seam_length | polyline arc length + extend + shorten + zigzag | Good after arc-length fix |
| AC10 purity | 5 tests (one per mutating op) | Good after fix |
| AC11 coverage ≥ 90% | 98% reported | Good |

**Gaps (tied to the Blocker above):** no AC explicitly calls out relative-command
handling, but B1 is the documented fix and its multi-pair path is untested.

## Verification I ran

- `git diff main..feat/01-pattern-svg-library-fixes` (reviewed full diff)
- `cd backend && uv run pytest --tb=short -q` → 218 passed
- `cd backend && uv run ruff check .` → clean
- `cd backend && uv run black --check .` → clean
- `cd backend && uv run pytest tests/test_pattern_ops.py --cov=lib.pattern_ops --cov-report=term-missing -q`
  → 98% coverage; uncovered lines 276, 292, 741, 755, 822, 845, 864, 896-897, 908
- Manually verified B1/B2 expected rotation values against the code's rotation
  matrix `[[cos, sin], [-sin, cos]]` for 90° CW (= `[[0,1],[-1,0]]`)
- Manually verified spread_at_line normal direction (`(line_vec[1], -line_vec[0])`
  points to +x for a vertical slash, matching the test's right-of-slash
  expectation)
- Manually verified zigzag arc length (5+5=10) against the fixed `_path_length`

## Questions for Steph

None blocking. Two optional follow-ups if the Blocker/Important are addressed:

1. Should the `_element_centroid` relative-command normalisation fix ride along
   with the B1 multi-pair test additions, or become its own spec? I'd lean
   toward its own micro-spec so the B1 fix branch stays scoped.
2. `M` multi-pair subpath-start behaviour (I4) — is it worth a targeted test
   (a path with `M 0,0 10,10 Z l 5,5`) or is this pathological enough that an
   inline code comment is sufficient?
