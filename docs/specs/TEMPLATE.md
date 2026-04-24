# Spec: [FEATURE NAME]

**Spec ID:** NN-name
**Status:** draft | ready-for-implementation | implemented | archived
**Created:** YYYY-MM-DD
**Depends on:** [other spec IDs, or "none"]

## What it does

One paragraph. What does this feature do, for whom, and why does it exist? Non-jargon. If a new team member read only this paragraph, they'd understand the feature's purpose.

## User-facing behavior

What does the user see / experience? If this feature has no direct user interaction (e.g. a backend library), describe what the calling code sees.

## Inputs and outputs

### Inputs
- `name: type` — description
- `name: type` — description

### Outputs
- `name: type` — description

### Errors
- What errors can occur? What should happen in each case?

## Acceptance criteria

Testable behaviors. Each item must be expressible as a test. Use format: "Given X, when Y, then Z."

- [ ] Given a valid pattern SVG, when we call `function_name(...)`, then the output SVG contains a new `<path>` element with id `bust-dart-left`.
- [ ] Given a pattern without a bust dart, when FBA is applied, then an error is raised with message "no bust dart found".
- [ ] ...

## Out of scope

What this feature explicitly does NOT do. Equally important as what it does — prevents scope creep.

- ...
- ...

## Technical approach

Brief description of how this will be implemented. Key data structures, algorithms, or integration points. If obvious from spec, can be one sentence.

## Dependencies

- External libraries needed: [list]
- Other specs that must be implemented first: [list]
- External services: [list]

## Testing approach

- Unit tests: [what should be covered]
- Integration tests: [what should be covered]
- Manual verification: [what Steph should eyeball]

## Open questions

Anything unresolved. Each question must be answered before `ready-for-implementation` status.

- ?

## Notes for implementer

Anything a subagent picking this up should know. Gotchas, conventions, pointers to reference code.
