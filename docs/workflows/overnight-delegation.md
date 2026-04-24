# Overnight Delegation Workflow

How to queue agent work while you sleep, and wake up to working code instead of broken mess.

## Core principle

**An agent is trustworthy only for work with a clear contract.** The contract is:

- A spec in `docs/specs/` with `ready-for-implementation` status
- Tests that define "done"
- Hooks that enforce standards automatically

Everything else is Steph's judgment. Agents execute; Steph decides.

## Pre-sleep checklist

Before you close your laptop:

- [ ] Specs are written and set to `ready-for-implementation` status
- [ ] Each spec has clear acceptance criteria (testable)
- [ ] Each spec lists its dependencies (and dependencies are already done)
- [ ] Git is clean — commit any WIP before queuing agent work
- [ ] You've pulled latest and there's nothing to rebase
- [ ] Environment variables are set; any required external services are reachable
- [ ] You're running on a branch, not main (safety)
- [ ] You know which specs are queued and in what order

## Queue pattern

The pattern for overnight:

```bash
# In Claude Code, say something like:
"Implement the following specs in order, using the implementer subagent for each,
and using a fresh context window between them. Stop and report if any spec fails
or has blocking ambiguity.

1. 03-measurement-to-body
2. 04-smpl-three-js-wrapper
3. 05-body-resize-ui-component

For each spec: run /implement, wait for completion, then /review before moving
on. If review returns NEEDS CHANGES, stop and log what needs changing — do not
try to fix it without my input. If review returns APPROVED, continue."
```

## What makes a spec safe to delegate

Score each spec before queuing. If any answer is "no," don't queue it.

- [ ] Is the spec self-contained? (Agent doesn't need to infer context from other sources.)
- [ ] Are acceptance criteria concrete and testable? ("Works correctly" is not testable.)
- [ ] Is the scope narrow? (< 1 file of implementation ideal; < 3 files acceptable.)
- [ ] Does success have an obvious definition? (Test pass + lint clean + type check.)
- [ ] Can it be done without architectural decisions? (If no, decision needs an ADR first.)
- [ ] Can it be done without destructive operations? (No DB migrations, no deleting other code, no force-pushing.)

## What's NOT safe to delegate overnight

- Prompts that need evaluation. Prompt iteration requires eyeballing outputs; run evals but make the prompt calls yourself.
- UI / UX work that requires visual judgment. Agents can write components; they can't tell if a component looks good.
- Anything involving live API calls that cost real money without a spending cap.
- Integration work between multiple subsystems where the integration approach is under-specified.
- Anything where the "correct" answer is a judgment call.
- The night before demo day. **Never touch main branch on Day 6 → 7.**

## Waking up

The protocol when you wake:

1. **Before opening anything else, read the agent's handoff notes** in each spec's "Implementation notes" section.
2. Check `git log` — how many commits ran overnight, do the messages make sense?
3. Run the full test suite before trusting anything.
4. Run lint and type-check.
5. Scan the diff yourself, not just the review. Look for:
   - New dependencies (should they be there?)
   - Changes outside the spec scope
   - Patterns that don't match the rest of the codebase
6. Run the app manually, do one smoke-test of the happy path.

Only then trust the night's work.

## When things go wrong

Signs an overnight session went bad:

- More than ~5 commits on a single spec (agent probably got stuck in a loop)
- Tests were skipped or marked `@pytest.mark.skip`
- `# noqa` or `eslint-disable` comments appeared
- New dependencies that weren't in the spec
- Files edited outside the spec's scope

If any of these happen: **revert the spec's commits**, read the agent's handoff notes to understand what went wrong, and do that spec yourself in the morning. One bad overnight run is a small tax; accepting bad code because you queued it is a big one.

## Cost note

Overnight agent runs use Managed Agents session time ($0.08/hour per active runtime) plus token costs. For a hackathon, budget maybe $10-30 total. Set a spending limit in your Anthropic console.

## Iteration

This workflow is v1. After each overnight run, note what went wrong and what could be tighter next time. Update this doc.
