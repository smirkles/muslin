# Spec: Hello-World Managed Agent

**Spec ID:** 09-hello-world-managed-agent
**Status:** implemented
**Created:** 2026-04-24
**Depends on:** none (uses the existing FastAPI scaffold and `backend/lib/` pattern)

## What it does

Proves end-to-end that Claude Opus 4.7 can be invoked from the Iris Tailor backend: an HTTP request comes in, the backend loads a prompt from `prompts/`, calls Claude via the Anthropic SDK, and returns Claude's text response. This is a trivial "hello world" — not a real diagnosis — whose only jobs are (a) verifying API keys / SDK wiring work, (b) establishing the `backend/lib/diagnosis/` package boundary so later multi-agent work can swap in Managed Agents without touching HTTP callers, and (c) seeding the `prompts/` directory pattern that Day 3 prompts will follow.

Per `CLAUDE.md`: "Managed Agents architecture is pending — write against the interface in `backend/lib/diagnosis/` so we can swap in later without rewriting callers." This spec creates the first such interface and its direct-SDK implementation. The guarantee this spec holds is that **HTTP routes keep routing through `backend/lib/diagnosis/`** — not that the lib's internal Protocol signature never changes.

## User-facing behavior

No end-user UI. The calling surface is an HTTP endpoint and the Python library it wraps:

1. A developer (Steph, or a later feature) sends `POST /dev/hello-agent` with a small JSON body.
2. The backend loads a prompt template from `prompts/hello_world/v1_baseline.md`, substitutes the user-supplied string, calls Claude Opus 4.7, and returns the completion text.
3. In the terminal / browser dev tools, Steph sees a real Claude response — confirming the wiring works.

If the Anthropic API key is missing or invalid, the endpoint returns a clear HTTP error rather than a stack trace.

## Inputs and outputs

### Library interface — `backend/lib/diagnosis/`

A minimal Protocol (or ABC) scoped to this hello-world. Day 3's multi-agent work is **expected** to widen this signature (images, system prompts, tool use). That widening does not require an ADR — only architectural shifts (e.g. moving orchestration out of `backend/lib/diagnosis/`, or changing the concrete backend away from Managed Agents once chosen) do.

```python
# backend/lib/diagnosis/agent.py
class DiagnosisAgent(Protocol):
    def run(self, prompt_name: str, variables: dict[str, str]) -> AgentResponse: ...

@dataclass(frozen=True)
class AgentResponse:
    text: str           # Claude's completion text
    model: str          # the model ID that served the request (e.g. "claude-opus-4-7-...")
    input_tokens: int
    output_tokens: int
```

- `backend/lib/diagnosis/anthropic_agent.py` — first implementation; reads `ANTHROPIC_API_KEY` from env, loads the prompt file from `prompts/<prompt_name>/v1_baseline.md`, substitutes `{{var}}` placeholders from `variables`, calls `anthropic.Anthropic().messages.create(...)`, returns `AgentResponse`.
- `backend/lib/diagnosis/prompts.py` — helper: `load_prompt(name: str, version: str = "v1_baseline") -> str` that reads from `prompts/<name>/<version>.md`, plus `substitute(template: str, variables: dict[str, str]) -> str` for `{{var}}` substitution. Centralises the "prompts are files, not strings" rule from `CLAUDE.md`.

### HTTP endpoint — `POST /dev/hello-agent`

Registered on the existing `routes/dev.py` router (dev-only, not for production).

#### Request body
- `name: str` (1–100 chars) — who to greet. Substituted into the prompt as `{{name}}`.

#### Response body (200)
- `text: str` — Claude's completion text.
- `model: str` — resolved model ID.
- `input_tokens: int`
- `output_tokens: int`

#### Errors
- **422** — `name` empty or > 100 chars (standard FastAPI validation).
- **500** — `ANTHROPIC_API_KEY` missing from env → body `{"detail": "ANTHROPIC_API_KEY not configured"}`.
- **502** — Anthropic SDK raised an error (network, auth, rate limit, etc.) → body `{"detail": "Claude API error"}`. Full exception logged server-side; not leaked to client.

### Prompt file — `prompts/hello_world/v1_baseline.md`

Plain markdown file loaded at request time. Contains `{{name}}` placeholder. Example content:

```
You are a friendly assistant for a sewing pattern tool called Iris Tailor.
Greet {{name}} in one short sentence and mention you're ready to help with pattern fitting.
Reply with only the greeting — no preamble, no markdown.
```

Versioned in git. Future changes create `v2_*.md` files rather than mutating `v1_baseline.md` (matches the eval harness convention called out in `evals/`).

### Env vars

```bash
# backend/.env.example (add to existing)
ANTHROPIC_API_KEY=           # required; leave blank in .env.example
ANTHROPIC_MODEL=claude-opus-4-7   # optional override; default hardcoded in agent
```

Never commit a real key. `.env.local` is gitignored (existing convention).

## Acceptance criteria

- [x] Given `prompts/hello_world/v1_baseline.md` exists, when `load_prompt("hello_world")` is called, then it returns the file contents as a string.
- [x] Given `prompts/hello_world/v1_baseline.md` does not exist, when `load_prompt("hello_world")` is called, then `PromptNotFound` (or `FileNotFoundError`) is raised with the attempted path included in the message.
- [x] Given a prompt containing `{{name}}`, when `substitute(template, {"name": "Steph"})` is called, then `{{name}}` is replaced with `Steph` and no other characters change.
- [x] Given the prompt references a `{{var}}` that isn't supplied in `variables`, when `substitute(...)` runs, then a `KeyError` (or domain-specific `PromptError`) is raised — no silent passthrough of `{{var}}`.
- [x] Given a mocked Anthropic client returning `content=[{"text": "Hi Steph!"}], usage={"input_tokens": 10, "output_tokens": 5}`, when `AnthropicAgent().run("hello_world", {"name": "Steph"})` is called, then the returned `AgentResponse` has `text="Hi Steph!"`, `input_tokens=10`, `output_tokens=5`, and `model` set to the configured model ID.
- [x] Given `ANTHROPIC_API_KEY` is unset, when `AnthropicAgent().run(...)` is called, then a `ConfigError` is raised with a message mentioning the env var name.
- [x] Given a valid request body `{"name": "Steph"}`, when `POST /dev/hello-agent` is called with the Anthropic client patched to return a canned response, then the response status is 200 and the body matches the documented `AgentResponse` shape.
- [x] Given `ANTHROPIC_API_KEY` is unset, when `POST /dev/hello-agent` is called, then the response status is 500 with `detail="ANTHROPIC_API_KEY not configured"`.
- [x] Given the mocked Anthropic client raises `anthropic.APIError`, when `POST /dev/hello-agent` is called, then the response status is 502 and the detail does not leak the original exception message verbatim.
- [x] Given an empty `name` or `name` longer than 100 chars, when `POST /dev/hello-agent` is called, then FastAPI returns 422.
- [x] `backend/lib/diagnosis/` contains no imports from `fastapi` or any HTTP framework (enforced by the test suite via an import check).
- [x] `uv run pytest` passes; `uv run ruff check . && uv run black --check .` exit 0.
- [x] A live smoke test marked `@pytest.mark.integration` exists that, when `ANTHROPIC_API_KEY` is set, actually hits the Anthropic API and asserts a non-empty `text` response. Skipped by default in `pytest` runs without the env var.

## Out of scope

- Multi-agent orchestration (that's Day 3, separate spec TBD).
- Streaming responses — this is single-shot only.
- Managed Agents SDK integration — we use the direct Anthropic SDK; the library boundary lets Managed Agents swap in later.
- Image / vision input — Day 3 will widen the Protocol to accept image bytes. Not in this spec.
- Any frontend UI. Calling `POST /dev/hello-agent` from the browser or curl is sufficient.
- Prompt evaluation harness — `evals/` is a separate spec.
- Retry/backoff, rate-limit handling, cost tracking. Log the usage numbers; that's it.
- Session / conversation memory. Each call is independent.
- Caching Claude responses.
- Authentication on the endpoint — it lives under `/dev` which is developer-only (same caveat as existing `/dev/reverse-string`).

## Technical approach

- `backend/lib/diagnosis/agent.py` defines `DiagnosisAgent` Protocol and `AgentResponse` dataclass.
- `backend/lib/diagnosis/anthropic_agent.py` implements `DiagnosisAgent` using `anthropic` Python SDK. Reads `ANTHROPIC_API_KEY` and optional `ANTHROPIC_MODEL` at construction; raises `ConfigError` if key missing when `run()` is invoked.
- `backend/lib/diagnosis/prompts.py` provides `load_prompt(name, version="v1_baseline")` and `substitute(template, variables)` as two separate functions so tests can hit each independently. Substitution uses `{{var}}` delimiters to avoid clashing with Python f-string or Jinja braces that might appear in prompts.
- `backend/routes/dev.py` gains `POST /dev/hello-agent`. Thin: validates input, constructs `AnthropicAgent()` (or pulls from a module-level singleton), calls `run()`, maps exceptions to HTTP codes, returns JSON. No prompt logic in the route.
- Dependency injection: the route looks up the agent via a tiny `get_agent()` factory so tests can patch it cleanly. Matches the testability pattern used by existing routes.

## Dependencies

- External libraries needed: `anthropic` (add to `backend/pyproject.toml`).
- Other specs that must be implemented first: none. (`01-pattern-svg-library` and later specs don't block this.)
- External services: Anthropic API. Requires an `ANTHROPIC_API_KEY` in `.env.local` for the live smoke test.

## Testing approach

- **Unit tests (mocked):** `backend/tests/test_hello_agent.py` covering `load_prompt`, `substitute`, and `AnthropicAgent.run()` with the Anthropic client patched. Cover happy path, missing env var, SDK exception, missing prompt file, missing template variable.
- **Route tests (mocked):** extend `backend/tests/test_routes_dev.py` (or create a new file) to cover the endpoint's 200 / 422 / 500 / 502 paths with `get_agent` patched.
- **Import-hygiene test:** a single test that imports every module in `backend/lib/diagnosis/` and asserts `fastapi` is not a transitive import of that package — enforces the "no HTTP concerns in lib" rule.
- **Live smoke test (`@pytest.mark.integration`):** one test that actually hits the Anthropic API when `ANTHROPIC_API_KEY` is present. Skipped otherwise. Run manually before merging and before demo day.
- **Manual verification:** Steph runs `uv run uvicorn main:app --reload`, then `curl -X POST http://localhost:8000/dev/hello-agent -H 'Content-Type: application/json' -d '{"name": "Steph"}'` — sees a real Claude greeting come back.

## Open questions

All resolved:

1. Trivial task: sewing-flavored greeting — "Hello Seamstress" style.
2. Model ID: `claude-opus-4-7` (env var `ANTHROPIC_MODEL` overrides).
3. Endpoint path: `/dev/hello-agent`.
4. SDK version: `anthropic>=0.40,<1` (latest stable).
5. No ADR — `CLAUDE.md` already encodes the rule.

## Notes for implementer

- **Never hardcode the prompt string** (`CLAUDE.md` critical rule 3). Always load from `prompts/hello_world/v1_baseline.md` via `load_prompt`.
- `backend/lib/diagnosis/` must not import FastAPI, Pydantic request/response models, or anything HTTP-flavored. Library is pure logic; route wiring lives in `backend/routes/dev.py`. This is the load-bearing invariant — the Protocol signature itself is allowed to evolve.
- Follow the existing `routes/dev.py` structure for the new endpoint — request/response Pydantic models with `model_config = ConfigDict(strict=True)`, thin handler, docstring warning that this is dev-only.
- Write failing tests first (per `CLAUDE.md` rule 5). Start with `test_load_prompt`, then `substitute`, then the agent, then the route.
- Day 3's multi-agent work will likely extend the Protocol to accept image bytes and optional system prompts. That's expected; do not over-engineer the Protocol now.
- If the Anthropic SDK changes its `messages.create(...)` response shape between now and Day 3, update only `anthropic_agent.py`; callers and tests should be unaffected.

## Implementation notes

### What was implemented

- `backend/lib/diagnosis/__init__.py` — package marker.
- `backend/lib/diagnosis/agent.py` — `DiagnosisAgent` Protocol, `AgentResponse` frozen dataclass, and `ConfigError` exception class.
- `backend/lib/diagnosis/prompts.py` — `load_prompt(name, version, prompts_root)` and `substitute(template, variables)`. The `prompts_root` parameter defaults to the repo-root `prompts/` directory, resolved from `__file__` at import time. Tests inject a `tmp_path` to avoid touching the real filesystem.
- `backend/lib/diagnosis/anthropic_agent.py` — `AnthropicAgent` concrete implementation using the Anthropic SDK. Reads `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` at `run()` time.
- `backend/routes/dev.py` — `POST /dev/hello-agent` endpoint with `HelloAgentRequest`, `HelloAgentResponse` Pydantic models, and `get_agent()` factory (patchable in tests).
- `prompts/hello_world/v1_baseline.md` — prompt file with `{{name}}` placeholder.
- `backend/pyproject.toml` — updated `anthropic>=0.25.0` to `anthropic>=0.40,<1`; added `integration` marker under `[tool.pytest.ini_options]`.
- `backend/.env.example` — added `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` entries.
- `backend/tests/test_hello_agent.py` — 18 unit tests (4 for `load_prompt`, 7 for `substitute`, 2 for `AgentResponse`, 4 for `AnthropicAgent`, 1 for import hygiene) plus 1 skipped integration test.
- `backend/tests/test_hello_agent_route.py` — 10 route tests covering 200/422/500/502 paths.

### Deviations from spec

- None. All acceptance criteria implemented exactly as specified.
- `anthropic>=0.25.0` was already present in `pyproject.toml` — updated in place rather than adding a duplicate (as advised).
- The `prompts_root` optional parameter on `load_prompt` and `AnthropicAgent.__init__` is an addition to support clean testing with `tmp_path`. It does not affect production behaviour (defaults to the repo-root `prompts/` directory).
- The `ConfigError` exception class is defined in `agent.py` alongside the Protocol (not in a separate `errors.py`). Kept small per "small files" convention.

### Open questions for Steph

- None. All spec open questions were pre-resolved.

### Cleanup report

- Acceptance criteria checked: 13 of 13
- Stray files removed: none found
- TODO/FIXME/HACK/XXX: none found in any changed file
- Linter/test result: PASS — `uv run pytest` 239 passed, 1 skipped; `ruff check .` and `black --check .` both exit 0
