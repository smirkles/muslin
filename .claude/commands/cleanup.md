---
description: Post-implementation cleanup — mark spec checkboxes, remove artifacts, verify linters and tests are green
argument-hint: spec ID (e.g. 02-string-reverse-utility)
---

Run a cleanup pass on the implementation of spec: $ARGUMENTS

## Steps

1. **Spec housekeeping**
   - Open `docs/specs/$ARGUMENTS.md`
   - Mark each acceptance criterion `[x]` that has a passing test (leave `[ ]` for any that are genuinely untested — don't silently tick them)
   - Confirm `**Status:**` is `implemented`

2. **Stray artifact check**
   - Run `git status` and flag any untracked files that should not be committed (temp files, debug scripts, misplaced `__pycache__`, literal brace-expansion directories like `{routes,lib`, etc.)
   - Remove any stray files that are clearly accidental; flag anything ambiguous for Steph

3. **TODO/FIXME scan**
   - `grep -rn "TODO\|FIXME\|HACK\|XXX"` across files changed in this implementation
   - List any found; resolve ones that are trivial, surface ones that need a decision

4. **Linter + test verification**
   - Backend: `cd backend && uv run pytest && uv run ruff check . && uv run black --check .`
   - Frontend: `cd frontend && pnpm test && pnpm lint` (skip with a note if frontend scaffold isn't set up yet)
   - All must exit 0 before cleanup is considered complete

5. **Git hygiene**
   - Confirm no `.env`, secrets, or credential files are staged or untracked
   - Confirm `uv.lock` is committed if `pyproject.toml` changed

6. **Cleanup report**
   Append a `## Cleanup notes` section to the spec's implementation notes with:
   - Checkboxes marked: N of M
   - Stray files removed (list) / none found
   - TODOs resolved (list) / surfaced for Steph (list) / none found
   - Linter/test result: PASS or list of failures
   - Any items that need Steph's attention before `/review`
