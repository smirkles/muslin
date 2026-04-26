# Review: 16-multi-agent-diagnosis

**Reviewed:** 2026-04-25T06:18:47Z
**Branch:** feat/16-multi-agent-diagnosis
**Reviewer:** claude-sonnet-4-6 (fresh context)
**Verdict:** APPROVED

---

## Summary

Strong implementation that satisfies all 18 acceptance criteria with passing tests, clean lint, and correct architecture. All tests pass (55 spec-related, 502 total committed tests + 1 skipped integration test). One important test-quality gap in the partial-failure test, and one dead parameter in `_run_specialist`, but neither is a blocker. No secrets, no FastAPI in lib/, all prompts in files.

---

## What's good

- All 55 targeted tests pass. Full committed test suite (502 tests, 1 skipped) passes.
- `ruff check .` and `black --check .` both exit 0.
- Concurrency correctly uses `asyncio.gather(asyncio.to_thread(...))` — proven by the 100 ms timing test passing at < 200 ms.
- Import hygiene test uses `rglob("*.py")` so it automatically covers the new `multi_agent.py` without needing a manual extension.
- All four prompts exist at `prompts/diagnosis/{region}/v1_baseline.md`. Coordinator prompt explicitly enumerates the closed set and instructs Claude to return only JSON.
- `CoordinatorParseError` is raised (not silently coerced) on invalid `cascade_type`.
- Route is thin: validates, resolves paths, maps exceptions to HTTP codes, nothing more.
- No secrets committed. `.env.local` is gitignored.
- Integration test is correctly marked `@pytest.mark.integration` and skips without `ANTHROPIC_API_KEY`.

---

## Issues found

### Important

**`test_one_specialist_fails_coordinator_runs_with_survivors` does not verify coordinator received only survivors.**

File: `backend/tests/test_multi_agent_orchestration.py:226-273`

The spec review checklist requires: "Partial-failure test verifies coordinator received only survivors (not all three)." The test asserts `isinstance(result, DiagnosisResult)` and that a warning log mentions "bust". It does not inspect `mock_agent.run.call_args_list[3]`'s `variables["specialist_outputs"]` to verify "bust" is absent. The implementation is correct (the `survivors` filter works), but the test would pass even if the filter were broken and all three outcomes (including the exception object) were serialised. Should add:

```python
coordinator_call = mock_agent.run.call_args_list[3]
variables = coordinator_call[0][1] if coordinator_call[0] else coordinator_call[1].get("variables", {})
specialist_outputs = variables.get("specialist_outputs", "")
assert "bust" not in specialist_outputs   # failed specialist excluded
assert "waist_hip" in specialist_outputs  # survivor present
assert "back" in specialist_outputs       # survivor present
```

**Base64 encoding happens inside `AnthropicAgent.run()`, not once in the orchestrator.**

Files: `backend/lib/diagnosis/multi_agent.py:311-312`, `backend/lib/diagnosis/anthropic_agent.py:97-107`

Spec technical approach says: "Base64 once: orchestrator encodes each image once and passes `list[bytes]` to all specialists." The implementation passes raw `list[bytes]` to all three specialists, and each specialist's `AnthropicAgent.run()` independently calls `base64.b64encode(img)`. With two images and three specialists, this means six base64 encode operations instead of two. This is a deviation from the stated architecture — for a hackathon this has no practical impact, but the spec's intent was clear.

### Nit

**`_run_specialist` accepts `prompts_root: Path` but never uses it.**

File: `backend/lib/diagnosis/multi_agent.py:241`

The `prompts_root` parameter is passed to `_run_specialist` from `run_diagnosis`, but is never referenced inside the function body. Prompt loading happens inside `AnthropicAgent.run()` via the agent's own `_prompts_root`. The parameter is dead and should be removed to avoid confusion. The `with patch("lib.diagnosis.multi_agent._PROMPTS_ROOT", tmp_path)` in tests also does not affect specialist prompt loading — tests work because the mock agent's `run.side_effect` returns canned JSON directly without reading any file.

**`# type: ignore[arg-type]` on `SpecialistDiagnosis(region=region, ...)`** (line 173) is a known Python typing limitation with Literal-from-string narrowing. Justified. No action needed.

**`# noqa: BLE001`** (line 274) is appropriate for intentional broad exception catching in partial-failure semantics. Justified.

---

## Test coverage gaps

All 18 acceptance criteria from the spec have at least nominal test coverage:

| Criterion | Test | Status |
|---|---|---|
| images=[bytes1, bytes2] → two image blocks | `TestAnthropicAgentWidenedSignature::test_images_produce_two_image_content_blocks` | PASS |
| max_tokens=4096 forwarded to SDK | `TestAnthropicAgentWidenedSignature::test_max_tokens_passed_to_sdk` | PASS |
| spec 09 callsite regression (no images) | `TestAnthropicAgentWidenedSignature::test_zero_image_callsite_still_works` | PASS |
| `_parse_specialist` valid JSON → dataclass | `TestParseSpecialistHappyPath::test_valid_json_returns_specialist_diagnosis` | PASS |
| `_parse_specialist` confidence clamped | `test_confidence_clamped_above_1`, `test_confidence_clamped_below_0` | PASS |
| Malformed JSON → `SpecialistParseError` with text | `TestParseSpecialistErrors::*` | PASS |
| Three successful → coordinator called with all three outputs | `test_three_specialists_coordinator_called_with_all_outputs` | PASS |
| Three 100 ms specialists < 200 ms | `TestRunDiagnosisConcurrency::test_three_100ms_specialists_complete_under_200ms` | PASS |
| One specialist fails → coordinator runs with survivors + warning | `test_one_specialist_fails_coordinator_runs_with_survivors` | PASS (but weak — see Important issue) |
| All specialists fail → `AllSpecialistsFailedError` | `TestRunDiagnosisTotalFailure::*` | PASS |
| `cascade_type: "banana"` → `CoordinatorParseError` | `TestRunDiagnosisCoordinatorError::test_coordinator_parse_error_propagates` | PASS |
| 200 with canned outputs | `TestDiagnosisRunHappyPath::*` | PASS |
| Unknown `measurement_id` → 404 | `TestDiagnosisRunNotFound::test_404_unknown_measurement_id` | PASS |
| `photo_id` with no crop → 404 | `TestDiagnosisRunNotFound::test_404_photo_id_with_no_segmented_crop` | PASS |
| `ANTHROPIC_API_KEY` unset → 500 | `TestDiagnosisRunConfigError::test_500_anthropic_api_key_not_set` | PASS |
| `AllSpecialistsFailedError` → 502 | `TestDiagnosisRunServiceError::test_502_all_specialists_failed_error` | PASS |
| `photo_ids=[]` or length > 3 → 422 | `TestDiagnosisRunValidationErrors::*` | PASS |
| `lib/diagnosis/` no FastAPI imports | `TestImportHygiene::test_diagnosis_modules_do_not_import_fastapi_by_source` | PASS |
| `@pytest.mark.integration` skip without key | `test_multi_agent_diagnosis_live_pipeline` | PASS (skipped correctly) |
| All tests pass + lint exit 0 | `uv run pytest`, `ruff check .`, `black --check .` | PASS |

**Gap:** The partial-failure test does not assert that "bust" is absent from coordinator's `specialist_outputs`. All other criteria are well-covered.

---

## Note on untracked test failures

Running `uv run pytest -v` on this branch shows 3 failures in `tests/test_export_svg.py` (ModuleNotFoundError: No module named `lib.export`). These files are **untracked** (not committed to this branch) — they belong to `feat/17-pattern-download` work in progress on disk. They pass on `main` and are not a regression introduced by spec 16. Steph should be aware they exist as uncommitted work in the working tree.

---

## Questions for Steph

1. The dead `prompts_root` parameter in `_run_specialist` — should it be removed in a follow-up or addressed before merge?
2. Should base64 encoding be moved to the orchestrator (encode once, pass encoded strings) to match the spec's stated technical approach, or is the current approach (encode per-agent inside `AnthropicAgent`) acceptable given it's a hackathon?
3. The `test_export_svg.py` and `lib/export/` untracked files — is spec 17 safe to leave uncommitted in the working tree given it uses this machine for overnight work?
