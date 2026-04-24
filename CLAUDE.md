# Muslin — Project Context

> The expert sewing friend you don't have. Home sewers upload a photo of themselves in a muslin (test garment) and get back an adjusted pattern that actually fits, with each change animated and explained.

Built solo by Steph for Anthropic's "Built with Opus 4.7" hackathon (April 2026).

## Where to look first

- **Full plan:** `docs/v2-plan.md` — THE source of truth for scope, week schedule, architecture.
- **Current specs:** `docs/specs/` — one file per feature, written before implementation.
- **Submission draft:** `docs/submission-materials.md`.
- **Architecture decisions:** `docs/decisions/` — ADRs for choices with long-term impact.

Always read `docs/v2-plan.md` at the start of a new session if you don't know what day we're on.

## Tech stack and why

- **Backend:** Python 3.11 + FastAPI, managed with `uv`. Python because of SMPL / libigl / SAM. FastAPI because Steph knows it.
- **Frontend:** Next.js 14+ App Router + Tailwind + GSAP. React because Steph knows it. Next.js for deployment ergonomics.
- **Testing:** Python with pytest. Frontend with Vitest + React Testing Library + Playwright (only for critical paths).
- **Reasoning:** Claude Opus 4.7 via Managed Agents (wired Day 3-4). During setup, direct API calls are fine — orchestration is isolated behind `backend/lib/diagnosis/` so we can swap without rewriting.
- **3D:** Three.js in browser. No cloth sim in V1.
- **Computer vision:** SAM 2 via Replicate (simpler than local).

## File structure rules

- `backend/lib/` is pure logic — no FastAPI imports, no HTTP concerns. Must be unit-testable in isolation.
- `backend/routes/` is thin — validate input, call into lib, return response.
- `frontend/src/lib/cascade_player/` is the GSAP animation engine. Must accept a cascade script (JSON) and play it without knowing anything about the pattern domain.
- `prompts/` stores all Claude prompts as versioned markdown files. **Never hardcode prompts in code.** Load them from files.
- `evals/` contains the prompt evaluation harness and fixtures.

## Code style

- **Python:** ruff + black. Type hints on all public functions. Docstrings on public functions (one line is fine).
- **TypeScript:** strict mode on. No `any` except in clearly marked escape hatches. Prettier default.
- **Both:** Functions over classes where reasonable. Small files. Descriptive names over clever ones.

## Critical rules

1. **Never commit secrets.** `.env` is gitignored. API keys live in `.env.local` (gitignored) and example shapes live in `.env.example`.
2. **All SVG manipulation goes through `backend/lib/pattern_ops/`.** Do not manipulate SVG elsewhere. This is the only way cascade reproducibility holds.
3. **All prompts are files, not strings.** Load from `prompts/` at runtime. Versioned in git. Run evals before and after any prompt change.
4. **Every feature has a spec.** No code without a spec in `docs/specs/`. No exceptions, even for "small" changes.
5. **Tests before implementation.** Write failing tests from the spec first, then make them pass. Skipping this will break overnight workflows.

## Commands

```bash
# Backend
cd backend && uv run uvicorn main:app --reload   # dev server
cd backend && uv run pytest                       # all tests
cd backend && uv run pytest tests/test_X.py       # single test file
cd backend && uv run ruff check . && uv run black --check .  # lint

# Frontend
cd frontend && pnpm dev                           # dev server
cd frontend && pnpm test                          # vitest
cd frontend && pnpm test:e2e                      # playwright
cd frontend && pnpm lint                          # eslint

# Evals
cd evals && uv run python run_eval.py --prompt-version v1_baseline
```

## Workflow for new features

1. You write or generate a spec in `docs/specs/NN-name.md` (use `/spec` command).
2. `/implement NN-name` — agent writes failing tests first, then implementation until passing.
3. `/review` — a fresh-context reviewer agent checks the output against the spec.
4. You review, commit.

For overnight work: queue specs, then `/implement` them in sequence. See `docs/workflows/overnight-delegation.md` (TBD).

## What NOT to do

- Don't "quickly add" features without a spec. You will regret it at review time.
- Don't manipulate SVG outside `pattern_ops/`.
- Don't inline prompts in code.
- Don't skip tests to save time. On this project, tests are how overnight work stays safe.
- Don't touch `main` the night before demo day (Day 7).
- Don't silently change architecture decisions. Write an ADR in `docs/decisions/`.

## Known quirks

- SMPL requires manual license registration at MPI website. Model files are gitignored; setup instructions in `docs/setup.md`.
- SAM 2 is used via Replicate API, not local — avoids GPU setup hell.
- Managed Agents architecture is pending — write against the interface in `backend/lib/diagnosis/` so we can swap in later without rewriting callers.
