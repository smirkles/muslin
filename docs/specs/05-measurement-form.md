# Spec: Measurement Form Component

**Spec ID:** 05-measurement-form
**Status:** implemented
**Created:** 2026-04-24
**Depends on:** 03-frontend-scaffold

## What it does

A React form component (`<MeasurementForm />`) where the user enters their body measurements. It validates inputs client-side and calls an `onSubmit` callback with the validated data when the user submits. This is the first real user-facing UI element in the product — the moment a user tells Iris Tailor about their body.

No API calls inside the component. The parent page wires it to the backend. This keeps the component fully testable in isolation.

## User-facing behavior

The user sees a form with seven labelled fields:
- **Full bust** (cm)
- **High bust** (cm)
- **Bust point to bust point** (cm)
- **Waist** (cm)
- **Hip** (cm)
- **Height** (cm)
- **Back length** (cm)

Each field has a brief helper text explaining where to measure. Validation happens on blur; after a field has been touched, it re-validates on every change. The submit button is disabled while any field is invalid or empty, or while `isLoading` is true. The form does not reset after submit (the parent decides what to do next).

## Inputs and outputs

### Props

```typescript
interface MeasurementFormProps {
  onSubmit: (measurements: Measurements) => void;
  isLoading?: boolean; // disables form while parent is calling the API
  serverErrors?: Record<keyof Measurements, string>; // per-field errors from backend 422
}

interface Measurements {
  bust_cm: number;
  high_bust_cm: number;
  apex_to_apex_cm: number;
  waist_cm: number;
  hip_cm: number;
  height_cm: number;
  back_length_cm: number;
}
```

### Validation rules (mirrors backend spec 07)

| Field | Min | Max |
|-------|-----|-----|
| bust_cm | 60 | 200 |
| high_bust_cm | 60 | 200 |
| apex_to_apex_cm | 10 | 30 |
| waist_cm | 40 | 200 |
| hip_cm | 60 | 200 |
| height_cm | 120 | 220 |
| back_length_cm | 30 | 60 |

### Errors

- Inline error per field: shown on blur, then live on each change once the field has been touched.
- `onSubmit` fires only when all fields pass client validation.
- Submit button is disabled while any field is invalid or empty, or while `isLoading` is true.
- `serverErrors` prop displays backend 422 errors beneath the relevant field (overrides client error for that field; cleared when the user edits the field).
- Use `parseServerErrors(detail)` from `measurements.ts` to translate a FastAPI 422 detail array into the `serverErrors` shape.

## Acceptance criteria

- [x] Given the form renders, then all 7 labelled fields are present with their helper text.
- [x] Given `bust_cm` is set to `59` (below minimum) and the field loses focus, then an inline error appears for that field only.
- [x] Given `bust_cm` is set to `201` (above maximum) and the field loses focus, then an inline error appears.
- [x] Given `apex_to_apex_cm` is set to `9` (below minimum) and the field loses focus, then an inline error appears.
- [x] Given `high_bust_cm` is set to `201` and the field loses focus, then an inline error appears.
- [x] Given a field has an error and the user corrects it (on change), then the error clears.
- [x] Given the form renders with all fields empty, then the submit button is disabled.
- [x] Given all 7 fields have valid values, then the submit button is enabled.
- [x] Given all 7 fields have valid values and the user clicks submit, then `onSubmit` is called once with the correct `Measurements` object.
- [x] Given `isLoading={true}`, then the submit button shows a loading state and all inputs are disabled.
- [x] Given `serverErrors={{ bust_cm: "Server says no" }}` is passed, then that error appears beneath the bust field.
- [x] Given a `serverError` is shown for a field and the user edits that field, then the server error clears.
- [x] `pnpm test` passes with all tests green.
- [x] `pnpm lint` exits 0.

## Out of scope

- Inch/cm toggle (cm only for V1).
- Calling the backend API directly from this component.
- Saving measurements to localStorage or any persistence.
- Any animation or transition on the form.
- Mobile-specific layout (desktop-first for V1).

## Technical approach

- Component at `frontend/src/components/MeasurementForm.tsx`.
- Use React controlled inputs with `useState` for each field value, error state, and touched state.
- Validation function `validateMeasurements(values)` exported from `frontend/src/lib/measurements.ts` — pure function, no React, mirrors the ranges from spec 07.
- No form library (react-hook-form, etc.) — too much overhead for 7 fields.
- Tailwind for styling — keep it clean and functional, not polished. Labels, inputs, error text, button. No design system needed yet.
- Track `touched: Record<keyof Measurements, boolean>` — field becomes touched on first blur; live validation only runs for touched fields. Submit is disabled until all fields are valid, so the handler just validates and calls `onSubmit`.

## Dependencies

- React (via Next.js scaffold from spec 03)
- Tailwind CSS (already in scaffold)
- No new packages

## Testing approach

- **Unit tests** in `frontend/src/lib/measurements.test.ts` — test `validateMeasurements` with boundary values for all 7 fields.
- **Component tests** in `frontend/src/components/MeasurementForm.test.tsx` — use React Testing Library:
  - Renders all 7 fields
  - Inline errors on blur with invalid values
  - Live error clearing on correction
  - Submit validates all-at-once when fields untouched
  - `onSubmit` called with correct data when all valid
  - `isLoading` disables inputs
  - `serverErrors` prop displays backend errors; clears on edit
- Run: `pnpm test`

## Implementation notes

### What was implemented

- `frontend/src/lib/measurements.ts` — `Measurements` interface (7 fields), `validateMeasurements()` pure function, `FIELD_META` (label + helper + range per field), `FIELD_ORDER` array for consistent field rendering.
- `frontend/src/components/MeasurementForm.tsx` — controlled form with `touched` state per field. Validates on blur, live-validates on change after first blur. Submit validates all fields at once; `onSubmit` only fires when all pass. `isLoading` disables all inputs and the button. `serverErrors` shows backend errors per field; clears on first edit of that field. Button uses `aria-label="Calculate my fit"` so the accessible name stays stable when text changes to "Calculating…".
- Tests: 34 unit tests (`validateMeasurements` + `parseServerErrors`), 15 component tests. 54 frontend tests total pass. ESLint exits 0.

### Deviations from spec

None. All 12 acceptance criteria implemented as specified.

## Open questions

None.

## Cleanup notes

- **Checkboxes marked:** 14 of 14
- **Stray files:** none in the feature branch; `docs/reviews/`, `docs/specs/08-*.md`, `docs/specs/09-*.md` are correctly untracked and belong to other work
- **TODOs/FIXMEs:** none found
- **Linter/test result:** PASS — 54/54 frontend tests, 187/187 backend tests, ESLint 0 errors, tsc clean, ruff + black clean
- **Stale content fixed:** test count in implementation notes updated (41 → 54); technical approach description of submit handler updated to reflect disabled-until-valid behaviour
- **Items for Steph:** none — ready to merge

## Notes for implementer

- Export `Measurements` type from `frontend/src/lib/measurements.ts` so it can be imported by pages later.
- Keep `validateMeasurements` pure (no side effects) — it will be reused by the page-level API call to validate before sending.
- Helper text for each field:
  - bust: "Around the fullest part of your bust, parallel to the floor"
  - high_bust: "Around your chest above the bust, level with your armpits"
  - apex_to_apex: "Distance between your two bust points (nipples)"
  - waist: "Around your natural waist, the narrowest point"
  - hip: "Around the fullest part of your hips, usually 20–23cm below your waist"
  - height: "Standing straight, without shoes"
  - back_length: "From the most prominent neck vertebra to your natural waist"
- Run cleanup checklist after implementation (see `.claude/commands/cleanup.md`).
