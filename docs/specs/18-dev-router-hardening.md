# Spec: Dev Router Hardening

**Spec ID:** 18-dev-router-hardening
**Status:** implemented
**Created:** 2026-04-25
**Depends on:** none

## What it does

Hides the `/dev/*` routes from the public OpenAPI schema and skips registering them entirely when the backend is running in production. The dev router (`backend/routes/dev.py`) exposes endpoints useful for local scaffold validation (`/dev/reverse-string`, `/dev/hello-agent`) but should not leak into `/docs`, `/redoc`, or a deployed production API surface. Default behaviour (no `APP_ENV` set) keeps the dev router registered so local development and existing tests are unaffected.

## User-facing behavior

No end-user impact. For API consumers: `/docs` and `/redoc` stop listing `/dev/*` routes regardless of environment. For operators: setting `APP_ENV=production` in the deployment environment causes the dev router not to mount, so `/dev/*` requests return 404.

## Inputs and outputs

### Inputs
- `APP_ENV: str | None` — environment variable read from `os.environ`. Only the literal `"production"` (case-sensitive) suppresses the dev router. Absent or any other value keeps the current behaviour.

### Outputs
- FastAPI application with the dev router either registered (with `include_in_schema=False`) or not registered at all.

### Errors
- None. `APP_ENV` is read defensively; missing variable is a valid state.

## Acceptance criteria

- [ ] Given `APP_ENV` is unset, when the app starts, then `POST /dev/reverse-string` returns 200 for a valid request body.
- [ ] Given `APP_ENV` is unset, when the app starts, then the OpenAPI schema at `/openapi.json` contains no paths starting with `/dev/`.
- [ ] Given `APP_ENV="production"`, when the app starts, then `POST /dev/reverse-string` returns 404.
- [ ] Given `APP_ENV="production"`, when the app starts, then the OpenAPI schema at `/openapi.json` contains no paths starting with `/dev/`.
- [ ] Given `APP_ENV="development"` (any non-`"production"` value), when the app starts, then `POST /dev/reverse-string` returns 200 and `/dev/*` is still excluded from the OpenAPI schema.
- [ ] `uv run pytest` passes; `uv run ruff check . && uv run black --check .` exit 0.

## Out of scope

- Gating the measurements or patterns routers.
- Introducing a broader settings/config module; a direct `os.environ.get` call is sufficient.
- Changing the contents of `backend/routes/dev.py`.
- Redirecting or custom-404-ing suppressed routes.
- Documenting `APP_ENV` in `.env.example`.

## Technical approach

One edit in `backend/main.py`: replace the unconditional `app.include_router(dev_router)` with:

```python
if os.environ.get("APP_ENV") != "production":
    app.include_router(dev_router, include_in_schema=False)
```

No other files change.

## Dependencies

- External libraries needed: none (`os` already imported in `backend/main.py`).
- Other specs that must be implemented first: none.

## Testing approach

- **Tests** in `backend/tests/test_main.py` using `TestClient`:
  - Default case: assert `/dev/reverse-string` returns 200 and `/openapi.json` omits `/dev/*` paths.
  - Production case: `monkeypatch.setenv("APP_ENV", "production")` + `importlib.reload(main)`; assert `/dev/reverse-string` returns 404. Restore state after.
- **Manual verification:** visit `http://localhost:8000/docs` — confirm no `/dev/*` entries.

## Open questions

None.

## Notes for implementer

- `os` is already imported — no new imports needed.
- Replace the existing DEV-ONLY comment block so it reflects the new gating behaviour.
- Production-mode tests must restore env and module state so they don't leak — scope `monkeypatch.setenv` + `importlib.reload` tightly to the single test.
- Existing `/dev/*` tests must continue to pass under the default (unset `APP_ENV`) path.

## Implementation notes

### What was implemented

- Single conditional in `backend/main.py` wraps `app.include_router(dev_router)` with `if os.environ.get("APP_ENV") != "production"`, and adds `include_in_schema=False` so `/dev/*` paths are excluded from OpenAPI schema in all environments.
- Six tests in `backend/tests/test_main.py` covering all acceptance criteria: dev routes accessible when APP_ENV unset, dev routes accessible when APP_ENV="development", dev routes return 404 when APP_ENV="production", and OpenAPI schema excludes /dev/* in all three cases.
- Tests use `monkeypatch.setenv/delenv` + `importlib.reload(main)` with explicit try/finally restoration to ensure full test isolation.

### Deviations from spec

None. Implementation is exactly the one-line change described in the technical approach.

### Open questions for Steph

None.

### New ADRs

None needed — change is mechanical and consistent with the existing pattern of using os.environ directly.
