# Spec: Frontend Scaffold

**Spec ID:** 03-frontend-scaffold
**Status:** ready-for-implementation
**Created:** 2026-04-24
**Depends on:** none

## What it does

Sets up the `frontend/` directory as a working Next.js 14 App Router project with TypeScript, Tailwind CSS, Vitest, and ESLint. The goal is a runnable scaffold — not a finished UI — so that all subsequent frontend specs have a consistent base to build on and the two stub files from spec 02 (`frontend/src/lib/utils.ts` and `frontend/src/lib/utils.test.ts`) actually run under `pnpm test`.

## User-facing behavior

No end-user features. The calling developer sees:

- `pnpm dev` starts a Next.js dev server on port 3000 with a blank index page showing the project name.
- `pnpm test` runs Vitest and passes all existing tests (including the 3 from spec 02's `utils.test.ts`).
- `pnpm lint` exits 0.
- `pnpm build` exits 0 (static export or standard build, whichever is simpler).

## Inputs and outputs

Not applicable — this is infrastructure, not a function.

## Acceptance criteria

- [ ] `frontend/package.json` exists with `name: "muslin-frontend"`, scripts for `dev`, `build`, `test`, `lint`.
- [ ] `pnpm dev` starts a Next.js 14 App Router dev server without errors.
- [ ] `frontend/src/app/page.tsx` renders a page with the text "Muslin" (any styling is fine).
- [ ] `frontend/src/app/layout.tsx` exists with a root layout wrapping children in a `<body>`.
- [ ] TypeScript is configured in strict mode (`tsconfig.json` with `"strict": true`).
- [ ] Tailwind CSS is installed and a `globals.css` imports the Tailwind directives.
- [ ] Vitest is configured (`vitest.config.ts`) with `jsdom` environment and React Testing Library.
- [ ] `pnpm test` runs and all 3 tests in `frontend/src/lib/utils.test.ts` pass.
- [ ] `pnpm lint` (ESLint) exits 0 against all files in `frontend/src/`.
- [ ] `pnpm build` completes without errors.
- [ ] No test files import from `@testing-library/react` in `utils.test.ts` — it's a pure function test, no DOM needed.

## Out of scope

- Any application UI beyond a blank index page with the project name.
- GSAP or Three.js installation (those come with the features that need them).
- Authentication, API routes, middleware.
- Deployment config (Vercel, Docker, etc.).
- Storybook or any other tooling not listed above.
- Playwright / E2E test setup (separate spec when needed).

## Technical approach

- Bootstrap with `pnpm create next-app` using flags: `--typescript`, `--tailwind`, `--app`, `--no-src-dir` is wrong — use `--src-dir` so files live under `src/` per the project structure in CLAUDE.md.
- After bootstrap, install Vitest: `pnpm add -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom`.
- Add `vitest.config.ts` pointing at `src/**/*.test.ts?(x)`.
- Add `"test": "vitest run"` to package.json scripts.
- The two stub files from spec 02 (`frontend/src/lib/utils.ts` and `frontend/src/lib/utils.test.ts`) already exist — do not overwrite them.
- If `create-next-app` would overwrite the existing `frontend/src/lib/` directory, scaffold into a temp directory and merge manually.

## Dependencies

- External: Node.js 20+, pnpm 8+
- Other specs: none (but spec 02's `frontend/src/lib/utils.ts` and `utils.test.ts` must be preserved)
- External services: none

## Testing approach

- **Acceptance tests:** run `pnpm test`, `pnpm lint`, `pnpm build` — all must exit 0.
- **Manual:** `pnpm dev` → open localhost:3000 → see "Muslin" on screen.
- **Regression:** confirm spec 02's `utils.test.ts` is the file running (check test output names match).

## Open questions

None.

## Notes for implementer

- The `frontend/` directory already has `src/lib/utils.ts` and `src/lib/utils.test.ts` from spec 02. Preserve these exactly — do not overwrite.
- `create-next-app` may prompt interactively — use `--yes` or pass all flags non-interactively to avoid blocking.
- CLAUDE.md says TypeScript strict mode — verify `tsconfig.json` has `"strict": true` after bootstrap (Next.js default may already include it).
- ESLint config: Next.js scaffold provides `.eslintrc.json` with `extends: ["next/core-web-vitals"]` — that's sufficient, don't add more rules.
- Commit as `feat: implement 03-frontend-scaffold` after all checks pass.
