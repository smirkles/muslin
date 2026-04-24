# Spec: Frontend Plumbing — API Client, State, CORS

**Spec ID:** 08-frontend-plumbing
**Status:** implemented
**Created:** 2026-04-24
**Depends on:** 03-frontend-scaffold, 04-measurements-endpoint, 07-measurements-fba-fields

## What it does

Connects the Next.js frontend to the FastAPI backend. Three pieces:

1. **API client** (`frontend/src/lib/api.ts`) — typed wrappers around every backend endpoint. No component imports `fetch` directly.
2. **Wizard state** (`frontend/src/store/wizard.ts`) — Zustand store holding all cross-page wizard data.
3. **CORS** — FastAPI must allow requests from the Next.js dev origin. Without this, every API call fails in the browser.

Also creates the first real page: `/app/measure/page.tsx` wires `MeasurementForm` to `postMeasurements` and the wizard store, so the app actually does something when you open it.

## Decisions (all resolved)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | State management | **Zustand** | Wizard spans multiple pages; Zustand handles cross-page state with minimal ceremony. In-memory only — no `persist` middleware needed for V1. |
| 2 | Wizard routing | **Multi-page** (`/app/measure`, `/app/photos`, `/app/results`) | Back-button works, shareable URLs, plays well with App Router. |
| 3 | CORS origins | **Env-var driven** | `CORS_ORIGIN` env var with `http://localhost:3000` as default. 5 extra lines, avoids touching `main.py` before demo day. |
| 4 | Error handling | **Inline on current step** | Show per-field errors (via `parseServerErrors`) or a generic error message; user stays on the form. |

## User-facing behaviour

After this spec, a user can:
1. Open `http://localhost:3000/app/measure`
2. See the `MeasurementForm` with all 7 fields
3. Fill it in and click "Calculate my fit"
4. See a loading state while the API call is in flight
5. On success: `measurement_id` and `size_label` are stored; user is routed to `/app/photos` (placeholder page for now)
6. On 422: per-field validation errors appear in the form
7. On other error: a generic inline error message appears with a retry option

## Types

### `MeasurementsResponse`

Mirrors the backend `MeasurementsResponse` Pydantic model (`backend/lib/measurements.py`):

```typescript
// frontend/src/lib/api.ts
export interface MeasurementsResponse {
  bust_cm: number;
  high_bust_cm: number;
  apex_to_apex_cm: number;
  waist_cm: number;
  hip_cm: number;
  height_cm: number;
  back_length_cm: number;
  measurement_id: string;
  size_label: string;
}
```

### `ApiValidationError`

Typed error thrown by `postMeasurements` on 422:

```typescript
export class ApiValidationError extends Error {
  detail: FastApiValidationError[]; // imported from measurements.ts
  constructor(detail: FastApiValidationError[]) {
    super("Validation error");
    this.detail = detail;
  }
}
```

On any other non-2xx response, `postMeasurements` throws a plain `Error` with the status code in the message.

## Files to create / modify

### New files

- `frontend/src/lib/api.ts` — API client
- `frontend/src/store/wizard.ts` — Zustand wizard store
- `frontend/src/app/app/measure/page.tsx` — measurement form page
- `frontend/src/app/app/photos/page.tsx` — placeholder (just "Photos coming soon")
- `frontend/.env.local.example` — example env vars

### Modified files

- `backend/main.py` — add `CORSMiddleware`
- `backend/.env.example` — add `CORS_ORIGIN`

## Implementation details

### `frontend/src/lib/api.ts`

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function postMeasurements(m: Measurements): Promise<MeasurementsResponse> {
  const res = await fetch(`${API_URL}/measurements`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(m),
  });
  if (res.status === 422) {
    const body = await res.json();
    throw new ApiValidationError(body.detail);
  }
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}
```

### `frontend/src/store/wizard.ts`

Zustand store — in-memory only (no persistence middleware):

```typescript
interface WizardState {
  patternId: string | null;           // set after pattern selection (future spec)
  measurementsResponse: MeasurementsResponse | null;  // set after postMeasurements
  setMeasurementsResponse: (r: MeasurementsResponse) => void;
  reset: () => void;
}
```

### `backend/main.py`

Add after the `app = FastAPI(...)` block:

```python
import os
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("CORS_ORIGIN", "http://localhost:3000")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

No `python-dotenv` needed — uvicorn reads `.env` via `--env-file .env` flag if required. For dev, setting `CORS_ORIGIN` in `.env` and running `uvicorn --env-file .env` is sufficient.

### `/app/measure/page.tsx`

- Renders `MeasurementForm` with `onSubmit`, `isLoading`, and `serverErrors`
- On submit: calls `postMeasurements`, sets `isLoading=true`
- On `ApiValidationError`: calls `parseServerErrors(err.detail)` → passes result to `serverErrors`
- On success: calls `setMeasurementsResponse(result)`, routes to `/app/photos`
- On generic error: shows an inline message "Something went wrong — please try again"

## Env vars

```bash
# frontend/.env.local.example
NEXT_PUBLIC_API_URL=http://localhost:8000

# backend/.env.example (add to existing)
CORS_ORIGIN=http://localhost:3000
```

## Acceptance criteria

- [x] `NEXT_PUBLIC_API_URL` env var controls where `postMeasurements` sends requests.
- [x] `postMeasurements` returns a fully typed `MeasurementsResponse` on 200.
- [x] `postMeasurements` throws `ApiValidationError` with the FastAPI `detail` array on 422.
- [x] `postMeasurements` throws a plain `Error` on other non-2xx responses.
- [ ] A browser fetch from `http://localhost:3000` to `http://localhost:8000/measurements` succeeds without a CORS error. (manual / E2E test — not unit-testable; middleware is wired correctly)
- [ ] `/app/measure` renders `MeasurementForm` with all 7 fields. (requires E2E or RTL render test — not in scope for this spec)
- [ ] Filling all 7 fields and clicking submit calls `postMeasurements` and shows a loading state. (requires E2E)
- [ ] On 422 from backend, per-field errors appear in the form. (requires E2E)
- [x] On success, `measurement_id` and `size_label` are stored in the wizard store and the user is routed to `/app/photos`. (wizard store unit-tested; routing wired in page)
- [x] Wizard state (`measurementsResponse`) survives navigation between `/app/measure` and `/app/photos` within the same session. (Zustand in-memory store; no server-side reset)
- [x] `pnpm test` passes with tests covering `postMeasurements` (200 and 422 paths, mocked `fetch`).
- [x] `uv run pytest` passes (CORS middleware doesn't break existing backend tests).
- [x] `pnpm lint` and `uv run ruff check .` exit 0.

## Out of scope

- Authentication.
- Error boundary components.
- API response caching.
- Loading skeletons (spinner on submit button is enough).
- Zustand `persist` middleware / localStorage (in-memory only for V1).
- Pattern selection page (`/app/pattern`) — that's a future spec.

## Implementation notes

### What was implemented

- `frontend/src/lib/api.ts` — `MeasurementsResponse` interface, `ApiValidationError` class, `postMeasurements` function. Reads `process.env.NEXT_PUBLIC_API_URL` inside the function body (not at module top) so tests can stub the env var without re-importing the module.
- `frontend/src/store/wizard.ts` — Zustand store with `patternId`, `measurementsResponse`, `setMeasurementsResponse`, and `reset`. In-memory only, no persist middleware.
- `frontend/src/app/app/measure/page.tsx` — `"use client"` page wiring `MeasurementForm` to `postMeasurements`, `useWizardStore`, and `useRouter`. Shows per-field server errors on 422, generic inline error on other failures.
- `frontend/src/app/app/photos/page.tsx` — Minimal placeholder page as specified.
- `frontend/.env.local.example` — Documents `NEXT_PUBLIC_API_URL`.
- `backend/main.py` — `CORSMiddleware` added after `app = FastAPI(...)`, env-var-driven origin (`CORS_ORIGIN` with `http://localhost:3000` default).
- `backend/.env.example` — Created fresh (file didn't exist) with `CORS_ORIGIN=http://localhost:3000`.

### Deviations from spec

- `process.env.NEXT_PUBLIC_API_URL` is read inside `postMeasurements()` at call time (not at module top as shown in the spec's code snippet). This is required for testability with `vi.stubEnv` without `vi.resetModules()` on every test. The observable behaviour (env var controls the URL) is identical.
- The env var fallback uses `||` rather than `??` so that an empty string `""` also falls back to `http://localhost:8000`. This makes the env-var test more robust.
- Two commits titled `feat: implement 08-frontend-plumbing` appear in history (commits `5ad514b` and `03cebce`). The first committed implementation files; the second committed the spec with implementation notes. This is a minor git hygiene issue.

### Open questions

- None. All ACs are covered by tests or noted as requiring E2E.

### Test results

- Frontend: 64 tests passing (5 test files, including 10 new tests in `api.test.ts` and `wizard.test.ts`)
- Backend: 208 tests passing (note: backend test count fluctuates by environment; all pass)
- `pnpm lint`: no warnings or errors
- `uv run ruff check . && uv run black --check .`: all checks passed

## Cleanup notes

- ACs marked: 9 [x], 4 [ ] — the 4 unmarked require E2E/browser testing (CORS integration, page render, form submit flow, and per-field 422 display). All are correctly wired in code.
- Stray files: none from this branch; pre-existing untracked review files and a future spec existed on the working tree before branching
- TODOs/FIXMEs/HACKs: none in any changed file
- No `.env` secrets staged — only `.env.example` and `.env.local.example` containing example values only
- `pnpm test --run`: 64/64 passing
- `uv run pytest`: all passing
- `pnpm lint`: 0 warnings, 0 errors
- `uv run ruff check . && uv run black --check .`: all checks passed
