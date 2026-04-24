---
description: Turn an idea into a structured feature spec
argument-hint: brief description of the feature
---

Invoke the spec-writer subagent to produce a feature spec for: $ARGUMENTS

The subagent should:
1. Read CLAUDE.md and docs/v2-plan.md for context
2. Read docs/specs/TEMPLATE.md for the required structure
3. Interview Steph about the feature using AskUserQuestion
4. Produce a spec file in docs/specs/ with status=draft
5. Present the draft for Steph's review
