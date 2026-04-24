# Review: 09-hello-world-managed-agent

**Reviewer:** fresh-context review agent
**Reviewed at:** 2026-04-24T14:15:06Z
**Branch:** `feat/09-hello-world-managed-agent`
**Base:** `main` (merge-base `0d5050e`)
**Commits under review:** `370f301` (failing tests), `e909ffc` (implementation)

## Summary

**NEEDS CHANGES**

The implementation is 12/13 on acceptance criteria and overall well-built — boundaries are clean, the AST-based import-hygiene test genuinely enforces the `lib/diagnosis/` contract, prompts are loaded from files (no hardcoded strings), the integration test is properly gated, and `uv run pytest` / `ruff` / `black` all pass. One real issue, though: the 500-response `detail` body produced by the real call path does **not** match the string documented in the spec. The only test that asserts the 500 body fakes the exception message in the mock, so it's green for the wrong reason. Fix that one string and this is an easy merge.

## What's good

- **Boundary is load-bearing and enforced.** `lib/diagnosis/agent.py` defines the `DiagnosisAgent` Protocol and `AgentResponse` frozen dataclass with zero HTTP surface. The AST-based import-hygiene test (`test_diagnosis_modules_do_not_import_fastapi_by_source`) walks each `.py` file in `lib/diagnosis/` and rejects any `import fastapi|starlette` or `from fastapi|starlette import ...` — this would actually catch a regression, not just vibe-check it.
- **Prompt file discipline.** `prompts/hello_world/v1_baseline.md` exists; the prompt text is nowhere hardcoded in Python. `load_prompt` + `substitute` are the only ingress points, both tested in isolation.
- **Substitution is strict.** `substitute` raises `KeyError` on unbound `{{var}}` rather than silently passing through — the spec explicitly called this out and the `test_substitute_no_silent_passthrough` test proves it.
- **Route thinness.** `routes/dev.py` validates input, calls `get_agent().run(...)`, and maps exceptions to HTTP codes — no prompt logic, no SDK logic. The `get_agent()` factory is the exact "patchable seam" the spec asked for, and the route tests use `patch("routes.dev.get_agent", ...)` without ever reaching the real SDK.
- **502 path is right.** `anthropic.APIError` → 502 with a hardcoded generic `"Claude API error"` detail; the original exception is logged via `logger.exception` server-side but never echoed to the client. `test_502_detail_does_not_leak_exception_message` asserts a sentinel token doesn't appear in `response.text`, which is stronger than just checking `detail`.
- **Integration test is correctly gated.** `test_anthropic_agent_live_smoke` is decorated with both `@pytest.mark.integration` and `@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"))`. Confirmed skipped during `uv run pytest` on a machine with no key set.
- **Dependencies and env vars match the spec.** `anthropic>=0.40,<1` in `pyproject.toml`; `integration` marker registered; `.env.example` gained `ANTHROPIC_API_KEY=` (blank) and `ANTHROPIC_MODEL=claude-opus-4-7`.

## Issues found

### Blocker

None — the item below is a public-contract violation but is a one-line fix.

### Important

- **Spec-violating 500 `detail` body — the real call path produces a different string than the spec documents, and the test masks it.**

  Spec (HTTP endpoint, Errors):
  > **500** — `ANTHROPIC_API_KEY` missing from env → body `{"detail": "ANTHROPIC_API_KEY not configured"}`.

  Actual implementation: `backend/lib/diagnosis/anthropic_agent.py:62-65` raises
  ```python
  raise ConfigError(
      "ANTHROPIC_API_KEY is not configured. "
      "Set ANTHROPIC_API_KEY in your environment or .env.local file."
  )
  ```
  …and `backend/routes/dev.py:92` does `raise HTTPException(status_code=500, detail=str(exc)) from exc`. So a real hit to the endpoint with no key returns `{"detail": "ANTHROPIC_API_KEY is not configured. Set ANTHROPIC_API_KEY in your environment or .env.local file."}`, not the documented string.

  Why the existing test is green anyway: `backend/tests/test_hello_agent_route.py:80-89` (`test_missing_api_key_returns_500`) sets `mock_agent.run.side_effect = ConfigError("ANTHROPIC_API_KEY not configured")` — the spec's exact string is invented in the mock. The test is effectively asserting "whatever string the mock raised is passed through to `detail`", not "the real ConfigError message matches the spec".

  The 502 path handles the analogous problem correctly by hardcoding `detail="Claude API error"` in the route and letting the long internal exception message go to logs only. Mirror that pattern for 500.

  **Suggested fix (pick one):**
  1. In `routes/dev.py:92`, hardcode the response body: `raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured") from exc` — keep the detailed message in the exception/log for developers.
  2. Or shorten the `ConfigError` string in `anthropic_agent.py` to the exact spec text `"ANTHROPIC_API_KEY not configured"`. This also requires updating `test_run_missing_api_key_raises_config_error` if it asserts anything stronger than substring containment (it currently asserts `"ANTHROPIC_API_KEY" in str(exc_info.value)`, which would still pass).

  **Suggested test hardening (regardless of which fix):** the route test should either (a) not fabricate the exception message — let the real `AnthropicAgent.run()` path raise by clearing `ANTHROPIC_API_KEY` from the env with `patch.dict(os.environ, {}, clear=True)` and not patching `get_agent`; or (b) keep the unit-style mock but set `side_effect = ConfigError("any developer-facing message")` and assert `response.json()["detail"] == "ANTHROPIC_API_KEY not configured"` to prove the route scrubs it. Either way, the assertion must pin the spec string, not echo the mock.

### Nit

- **`backend/lib/diagnosis/anthropic_agent.py:32-40` — `self._model` is effectively dead.** `__init__` reads `ANTHROPIC_MODEL` into `self._model`, but `run()` re-reads `os.environ.get("ANTHROPIC_MODEL", self._model)`. If `ANTHROPIC_MODEL` is set in the process env, `os.environ.get` will always find it; `self._model` is used only in the pathological case where the env var was set at construction and unset before `run()`. Either drop `self._model` entirely and read the env var once in `run()`, or honour `self._model` as a captured-at-init value and stop re-reading the env var.
- **`backend/lib/diagnosis/prompts.py:77` — `# type: ignore[type-arg]` without a justification comment.** `re.Match` could be spelled `re.Match[str]` and drop the ignore, matching `CLAUDE.md`'s "no unjustified suppressions" preference.
- **Branch is behind `main` by the `python-dotenv` hotfix (`24897b6`).** Not a merge conflict — `main.py` is untouched on the feature branch — but the merge will be a real three-way merge, not fast-forward. After merging, the endpoint will pick up `ANTHROPIC_API_KEY` from `.env.local` automatically. Flag only.

## Test coverage gaps

Every spec acceptance criterion has a test, but one of them tests the wrong thing:

| Acceptance criterion | Test(s) | Notes |
|---|---|---|
| `load_prompt` returns file contents | `TestLoadPrompt::test_load_prompt_returns_file_contents` | OK |
| Missing prompt raises `FileNotFoundError` with path | `TestLoadPrompt::test_load_prompt_missing_file_raises_file_not_found`, `..._error_includes_path` | OK |
| `substitute` replaces `{{name}}` | `TestSubstitute::test_substitute_replaces_placeholder` | OK |
| Missing `{{var}}` raises `KeyError`, no silent passthrough | `test_substitute_missing_key_raises_key_error`, `..._no_silent_passthrough` | OK |
| `AnthropicAgent.run` returns correct `AgentResponse` fields | `test_run_returns_agent_response_with_correct_fields`, `..._test_run_model_matches_configured_model` | OK |
| Missing `ANTHROPIC_API_KEY` raises `ConfigError` mentioning the env var | `test_run_missing_api_key_raises_config_error` | OK (substring assertion) |
| `POST /dev/hello-agent` 200 with documented shape | `test_valid_request_returns_200_with_agent_response_shape` | OK |
| Missing key → 500 with **detail `"ANTHROPIC_API_KEY not configured"`** | `test_missing_api_key_returns_500` | **GAP — the mock fabricates the spec string; the real call path produces a different detail. See Important issue above.** |
| SDK `APIError` → 502 without leaking message | `test_anthropic_sdk_error_returns_502`, `..._test_502_detail_does_not_leak_exception_message` | OK |
| Empty / >100-char `name` → 422 | `test_empty_name_returns_422`, `..._test_name_over_100_chars_returns_422` | Boundary `=100` also covered |
| No FastAPI imports in `lib/diagnosis/` | `test_diagnosis_modules_do_not_import_fastapi_by_source` | AST walk; catches both `import` forms |
| Lint + tests green | See "Local verification" below | OK |
| Integration smoke test, skipped without key | `test_anthropic_agent_live_smoke` with `@pytest.mark.integration` + `@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"))` | OK |

Bonus tests that go beyond the spec (all welcome): `test_agent_response_is_frozen_dataclass`, `test_agent_response_is_immutable`, `test_name_exactly_100_chars_returns_200`, `test_missing_name_field_returns_422`, `test_numeric_name_returns_422` (exercises Pydantic `strict=True`).

## Local verification

Ran on branch `feat/09-hello-world-managed-agent`:

```
uv run pytest                 # 239 passed, 1 skipped
uv run ruff check .           # All checks passed!
uv run black --check .        # 22 files would be left unchanged.
uv run pytest -m integration  # 1 skipped, 18 deselected (expected — no ANTHROPIC_API_KEY set)
```

CLAUDE.md compliance:

- Rule 1 (no secrets) — `.env.example` has blank `ANTHROPIC_API_KEY=`; no key in diff.
- Rule 2 (SVG through `pattern_ops/`) — N/A; spec touches no SVG.
- Rule 3 (prompts are files) — `prompts/hello_world/v1_baseline.md` is the only prompt text; no hardcoded strings in Python.
- Rule 4 (spec exists) — `docs/specs/09-hello-world-managed-agent.md` present.
- Rule 5 (tests before impl) — commit order confirms it: `370f301 test: add failing tests...` precedes `e909ffc feat: implement...`.

## Questions for Steph

None. The ambiguity around the 500 body is resolved by the spec itself — the spec documents the exact string — so this is a straightforward bring-the-code-up-to-spec fix.

## Recommendation

**NEEDS CHANGES.** One small fix to align the 500 response body with the documented contract (plus a test that actually pins the spec string to the real call path), then re-review. The three nits are optional polish — feel free to roll any of them in while you're in the file, but they don't gate the merge.
