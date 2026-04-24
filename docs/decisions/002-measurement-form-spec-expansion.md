# ADR 002: Measurement Form — Mid-Flight Spec Expansion and Submit-Button UX

**Status:** Accepted
**Date:** 2026-04-24

## Context

Spec 05 (measurement form) was written against the 5-field `Measurements` model from spec 04. While the feature branch was open, spec 07 (FBA fields) merged to `main` and expanded the backend model to 7 fields (`high_bust_cm`, `apex_to_apex_cm` added). A 5-field form submitting to a 7-field backend would 422 immediately.

The implementer expanded the form to 7 fields mid-flight rather than stopping to flag the dependency change — a process violation (implementers should flag, not edit specs). However, the expansion itself is the correct technical decision, so the rewritten 7-field spec was accepted as authoritative rather than reverting.

The original spec also specified "submit button disabled until all fields valid." The implementer quietly reversed this to "always enabled; errors revealed on click." This was reversed back to "disabled until valid" during post-review fixes.

## Decisions

### 1. Accept the 7-field spec rewrite

The 5-field → 7-field expansion is forced by the backend model. Reverting to a 5-field frontend would require either accepting instant 422s on every submit or adding dead fields to the backend. Neither is acceptable.

Going forward: if a dependency spec changes the contract a feature branch depends on, the implementer must stop and flag it rather than editing the spec themselves. Noted in `.claude/agents/implementer.md`.

### 2. Submit button disabled until all fields valid

"Disabled until valid" is the right UX for a measurement form:

- The form has 7 required numeric fields. A blank button gives users nothing to click toward — they must fill every field. The disabled state makes the goal legible.
- "Always enabled / errors on click" works well on forms where partial submission is possible (search, filters). Here, every field is required — there is no partial valid state.
- "Always enabled" hides errors until submit. "Disabled until valid" surfaces errors immediately on blur as users work through the form, which is more helpful.

### 3. parseServerErrors lives in measurements.ts

FastAPI 422 errors arrive as `{ detail: [{ loc, msg, type }] }`. The component's `serverErrors` prop expects `Partial<Record<keyof Measurements, string>>`. The translation function `parseServerErrors(detail)` is measurements-domain logic and lives in `frontend/src/lib/measurements.ts` alongside `validateMeasurements`.

## Consequences

- The `MeasurementForm` component now has 7 fields matching the backend model.
- The submit button is disabled until all 7 fields pass client-side validation.
- `parseServerErrors` is available for the page layer (spec 08) to translate FastAPI 422 responses before passing them as `serverErrors`.
- The spec/implement/review loop was bent but not broken. Process note added to implementer agent.

## References

- `docs/specs/05-measurement-form.md` — expanded spec
- `docs/specs/07-measurements-fba-fields.md` — dependency that triggered the expansion
- `frontend/src/lib/measurements.ts` — `validateMeasurements`, `parseServerErrors`
- `frontend/src/components/MeasurementForm.tsx` — component implementation
