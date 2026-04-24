#!/usr/bin/env bash
# Post-edit hook: runs lightweight validation after Claude Code edits a file.
# The goal is to surface problems fast (seconds, not minutes) so Claude can
# self-correct without a full test suite run on every change.
#
# Scope:
#   - Python edits → ruff check + type check on the single file
#   - TypeScript/JSX edits → eslint on the single file
#   - Test files → run just that test file
#   - Anything else → no-op
#
# Not in this hook:
#   - Full test suite (too slow for every edit; run manually or on commit)
#   - Formatting (done by editor/pre-commit, not here)

set -euo pipefail

FILE="${1:-}"

if [ -z "$FILE" ]; then
  exit 0
fi

# Skip if file doesn't exist (e.g. was deleted)
if [ ! -f "$FILE" ]; then
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

case "$FILE" in
  backend/**/*.py|evals/**/*.py)
    cd backend
    uv run ruff check "../$FILE" || exit 1
    # If it's a test file, run just that test
    if [[ "$FILE" == *"/tests/"* ]] || [[ "$FILE" == *"test_"* ]]; then
      uv run pytest "../$FILE" -q || exit 1
    fi
    ;;

  frontend/**/*.ts|frontend/**/*.tsx|frontend/**/*.js|frontend/**/*.jsx)
    cd frontend
    pnpm eslint "../$FILE" || exit 1
    if [[ "$FILE" == *".test."* ]] || [[ "$FILE" == *".spec."* ]]; then
      pnpm vitest run "../$FILE" || exit 1
    fi
    ;;

  *)
    # Non-code files (markdown, config, etc.) - no validation
    exit 0
    ;;
esac

exit 0
