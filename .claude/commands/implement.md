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
0. Create and check out a feature branch: `git checkout -b feat/$ARGUMENTS` — ALL work happens on this branch, never on main.
1. Read spec + CLAUDE.md + dependencies
2. Write failing tests first, commit them (to the feature branch)
3. Implement until tests pass
4. Refactor with tests green
5. Update spec with implementation notes, set status to "implemented"
6. Commit with "feat: implement $ARGUMENTS" (to the feature branch)
7. Run /cleanup $ARGUMENTS — see `.claude/commands/cleanup.md` for the full checklist. The cleanup report must appear in the subagent's final summary so Steph can see what was found and fixed without reading the spec file.
8. Report the branch name (`feat/$ARGUMENTS`) in the final summary so Steph can review and merge.
