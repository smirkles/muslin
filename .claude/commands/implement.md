---
description: Implement a feature spec using TDD
argument-hint: spec ID (e.g. 01-pattern-svg-library)
---

Invoke the implementer subagent to implement the spec with ID: $ARGUMENTS

Verify first that:
1. The spec exists at docs/specs/$ARGUMENTS.md
2. Its status is "ready-for-implementation"

If either check fails, stop and report to Steph.

Otherwise, the subagent should follow its standard TDD process:
1. Read spec + CLAUDE.md + dependencies
2. Write failing tests first, commit them
3. Implement until tests pass
4. Refactor with tests green
5. Update spec with implementation notes, set status to "implemented"
6. Commit with "feat: implement $ARGUMENTS"
