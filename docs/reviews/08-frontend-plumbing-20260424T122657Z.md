# Review: 08-frontend-plumbing

**Reviewed:** 2026-04-24 12:26 UTC
**Branch:** `feat/08-frontend-plumbing`
**Spec:** `docs/specs/08-frontend-plumbing.md`

## Summary

**APPROVED**

Spec is cleanly implemented. All unit-testable acceptance criteria are covered by tight tests, lint/type/format/test suites all pass on both frontend and backend, no SVG manipulation leaks, no hardcoded prompts, no `any` / `ts-ignore` / `eslint-disable`, and no secrets committed. The four E2E-only ACs (CORS integration, page render, submit flow, per-field 422 display) are correctly marked as such and are wired in code in a way that should work when exercised in the browser.

## What's good

- **Clean typed API client.** `postMeasurements` returns a precise `MeasurementsResponse`, throws a bespoke `ApiValidationError` on 422, and a plain `Error` otherwise — exactly matching the spec contract. `ApiValidationError` sets `this.name`, which the spec didn't require but is a nice touch for debugging.
- **Good testability deviation.** Reading `process.env.NEXT_PUBLIC_API_URL` inside the function rather than at module scope is sensibly justified in the spec's implementation notes — the observable behaviour is identical and the env-var test is simpler.
- **Tests are tight.** `api.test.ts` uses `vi.stubGlobal("fetch", …)` and asserts both on the thrown type and the payload shape. The 500 test asserts _not_ `ApiValidationError`, which guards against regression of the 422 branch swallowing all errors.
- **Zustand store is minimal and correct.** Tests reset between cases via the store's own `reset` action. Initial null state, set, and reset are all asserted.
- **Measure page wiring is complete.** `setGenericError(null)` + `setServerErrors({})` at the top of `handleSubmit` guarantees stale state doesn't leak between attempts. The `role="alert"` on the generic error banner is a nice accessibility touch.
- **CORS middleware is env-var driven** with a sensible default, and existing backend tests (208 passing) still pass — confirming the middleware doesn't interfere.
- **No secrets staged.** Only `.env.example` and `.env.local.example` with placeholder values are committed.

## Verification results

| Command | Result |
|---|---|
| `pnpm test --run` | 64/64 passing (5 files) |
| `pnpm lint` | 0 warnings, 0 errors |
| `npx tsc --noEmit` | clean |
| `uv run pytest -q` | 208/208 passing |
| `uv run ruff check .` | all checks passed |
| `uv run black --check .` | 16 files unchanged |

## Acceptance-criterion coverage

| # | AC | Coverage |
|---|----|----------|
| 1 | `NEXT_PUBLIC_API_URL` controls request URL | `api.test.ts` — "uses NEXT_PUBLIC_API_URL env var to build the request URL" + "falls back to http://localhost:8000 when NEXT_PUBLIC_API_URL is not set" |
| 2 | 200 → typed `MeasurementsResponse` | `api.test.ts` — "returns a typed MeasurementsResponse on 200" asserts exact equality + two specific keys |
| 3 | 422 → `ApiValidationError` with `detail[]` | `api.test.ts` — "throws ApiValidationError with detail array on 422" asserts type _and_ payload |
| 4 | Other non-2xx → plain `Error` with status | `api.test.ts` — "throws a plain Error on non-2xx non-422 response" asserts message _and_ negative type |
| 5 | CORS browser fetch succeeds | **E2E-only, correctly flagged** — middleware wired in `backend/main.py` with env-driven origin |
| 6 | `/app/measure` renders `MeasurementForm` | **E2E-only, correctly flagged** — page imports and renders the form |
| 7 | Submit calls `postMeasurements` + loading state | **E2E-only, correctly flagged** — `handleSubmit` sets `isLoading=true/false` around the call |
| 8 | 422 → per-field errors in form | **E2E-only, correctly flagged** — `parseServerErrors(err.detail)` fed into `serverErrors` prop |
| 9 | On success, `measurement_id` + `size_label` stored & route to `/app/photos` | `wizard.test.ts` — `setMeasurementsResponse` stores the full response (including `measurement_id` + `size_label`); routing wired in page via `router.push("/app/photos")` |
| 10 | Wizard state survives nav between pages | `wizard.test.ts` — state is module-level Zustand store (persists across component remounts within a session) |
| 11 | `pnpm test` passes with `postMeasurements` coverage | 64/64 passing |
| 12 | `uv run pytest` passes with CORS in place | 208/208 passing |
| 13 | `pnpm lint` + `uv run ruff check .` exit 0 | Both clean |

## Issues found

None rising to Blocker or Important.

### Nits

- **Nit — `frontend/src/app/app/measure/page.tsx:45`**: The spec says "On other error: a generic inline error message appears **with a retry option**". There's no explicit retry button — the user effectively retries by re-submitting the form. The form remains interactive, so this works in practice, but an explicit "Retry" affordance (or a sentence like "Please try again") is what the spec's wording implies. The current text "Something went wrong — please try again" reads as an instruction to retry via the form, which is arguably fine. Flagging for Steph's awareness; not worth blocking on.
- **Nit — commit history**: Two commits both titled `feat: implement 08-frontend-plumbing` (`5ad514b` and `03cebce`). Noted by the implementer in the spec itself. Safe to squash at merge time, or leave — no functional impact.
- **Nit — `api.ts:30`**: Uses `||` instead of `??` for the env-var fallback. Documented as a deliberate deviation to handle empty-string env vars. Reasonable; just worth remembering if `NEXT_PUBLIC_API_URL="0"` ever becomes meaningful (it never will).

## Test coverage gaps

None that are in-scope for this spec. Page-level behaviours (form submit round-trip, routing on success, loading state, 422 per-field display) are explicitly flagged as E2E-only in the spec. An RTL test of `MeasurePage` could be added later to lock in the success-path routing and generic-error banner without needing Playwright, but that's optional and not required by the spec.

## Questions for Steph

None. All ACs resolved; deviations from the spec text are documented in the implementation notes and match observable behaviour.
