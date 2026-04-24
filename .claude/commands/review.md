---
description: Review an implemented feature against its spec
argument-hint: spec ID (e.g. 01-pattern-svg-library)
---

Invoke the reviewer subagent to review the implementation of: $ARGUMENTS

The reviewer should operate in a fresh context window — do not pass it any prior conversation state.

The subagent should:
1. Read the spec at docs/specs/$ARGUMENTS.md
2. Read CLAUDE.md for project conventions
3. Use git diff to identify what changed
4. Verify each acceptance criterion has a passing test
5. Check for common issues (hardcoded prompts, out-of-scope code, type issues, lint, etc.)
6. Check test quality, not just test existence
7. Write a structured review to docs/reviews/$ARGUMENTS-{timestamp}.md
8. Report APPROVED / NEEDS CHANGES / BLOCKED to Steph

The reviewer does NOT modify code. It only reviews.
