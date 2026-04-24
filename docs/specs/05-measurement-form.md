# Spec: Measurement Form Component

**Spec ID:** 05-measurement-form
**Status:** ready-for-implementation
**Created:** 2026-04-24
**Depends on:** 03-frontend-scaffold

## What it does

A React form component (`<MeasurementForm />`) where the user enters their body measurements. It validates inputs client-side and calls an `onSubmit` callback with the validated data when the user submits. This is the first real user-facing UI element in the product — the moment a user tells Muslin about their body.

No API calls inside the component. The parent page wires it to the backend. This keeps the component fully testable in isolation.

## User-facing behavior

The user sees a form with five labelled fields:
- **Full bust** (cm)
- **Waist** (cm)
- **Hip** (cm)
- **Height** (cm)
- **Back length** (cm)

Each field has a brief helper text explaining where to measure (e.g. "Measure around the fullest part of your bust"). A "Calculate my fit" submit button is disabled until all fields have valid values. If a field is empty or out of range, an inline error appears beneath it. On valid submit, the `onSubmit` callback fires with the measurements object. The form does not reset after submit (the parent decides what to do next).

## Inputs and outputs

### Props

```typescript
interface MeasurementFormProps {
  onSubmit: (measurements: Measurements) => void;
  isLoading?: boolean; // disables form while parent is calling the API
}

interface Measurements {
  bust_cm: number;
  waist_cm: number;
  hip_cm: number;
  height_cm: number;
  back_length_cm: number;
}
```

### Validation rules (mirrors backend spec 04)

| Field | Min | Max |
|-------|-----|-----|
| bust_cm | 60 | 200 |
| waist_cm | 40 | 200 |
| hip_cm | 60 | 200 |
| height_cm | 120 | 220 |
| back_length_cm | 30 | 60 |

### Errors

- Inline error per field: shown on blur or on submit attempt.
- Submit button is disabled while any field is invalid or empty.

## Acceptance criteria

- [ ] Given the form renders, then all 5 labelled fields are present with their helper text.
- [ ] Given all fields are empty, then the submit button is disabled.
- [ ] Given `bust_cm` is set to `59` (below minimum) and the field loses focus, then an inline error appears for that field.
- [ ] Given `bust_cm` is set to `201` (above maximum), then an inline error appears.
- [ ] Given all 5 fields have valid values, then the submit button is enabled.
- [ ] Given all fields valid and the user clicks submit, then `onSubmit` is called once with the correct `Measurements` object.
- [ ] Given `isLoading={true}`, then the submit button shows a loading state and all inputs are disabled.
- [ ] Given a field has an error and the user corrects it, then the error clears.
- [ ] `pnpm test` passes with all tests green.
- [ ] `pnpm lint` exits 0.

## Out of scope

- Inch/cm toggle (cm only for V1).
- Calling the backend API directly from this component.
- Saving measurements to localStorage or any persistence.
- Any animation or transition on the form.
- Mobile-specific layout (desktop-first for V1).

## Technical approach

- Component at `frontend/src/components/MeasurementForm.tsx`.
- Use React controlled inputs with `useState` for each field value and error state.
- Validation function `validateMeasurements(values)` exported from `frontend/src/lib/measurements.ts` — pure function, no React, mirrors the ranges from spec 04.
- No form library (react-hook-form, etc.) — too much overhead for 5 fields.
- Tailwind for styling — keep it clean and functional, not polished. Labels, inputs, error text, button. No design system needed yet.

## Dependencies

- React (via Next.js scaffold from spec 03)
- Tailwind CSS (already in scaffold)
- No new packages

## Testing approach

- **Unit tests** in `frontend/src/lib/measurements.test.ts` — test `validateMeasurements` with boundary values for each field.
- **Component tests** in `frontend/src/components/MeasurementForm.test.tsx` — use React Testing Library:
  - Renders all fields
  - Inline errors on blur with invalid values
  - Submit button disabled/enabled states
  - `onSubmit` called with correct data
  - `isLoading` disables inputs
- Run: `pnpm test`

## Open questions

None.

## Notes for implementer

- Export `Measurements` type from `frontend/src/lib/measurements.ts` so it can be imported by pages later.
- Keep `validateMeasurements` pure (no side effects) — it will be reused by the page-level API call to validate before sending.
- Helper text for each field:
  - bust: "Around the fullest part of your bust, parallel to the floor"
  - waist: "Around your natural waist, the narrowest point"
  - hip: "Around the fullest part of your hips, usually 20–23cm below your waist"
  - height: "Standing straight, without shoes"
  - back_length: "From the most prominent neck vertebra to your natural waist"
- Run cleanup checklist after implementation (see `.claude/commands/cleanup.md`).
