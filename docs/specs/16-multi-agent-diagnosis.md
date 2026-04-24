# Spec: Multi-Agent Fit Diagnosis

**Spec ID:** 16-multi-agent-diagnosis
**Status:** ready-for-implementation
**Created:** 2026-04-25
**Depends on:** 09-hello-world-managed-agent, 11-photo-upload, 12-sam2-segmentation

## What it does

Runs three specialist Claude Opus 4.7 agents (bust, waist/hip, back) against the segmented muslin photos in parallel, then a coordinator agent synthesises their outputs into a single `DiagnosisResult` with a `cascade_type` that drives which adjustment cascade runs next. This is the headline feature of the hackathon: multi-agent diagnosis demonstrates that Claude can reason like a panel of fit experts. The implementation uses the direct Anthropic SDK via the `DiagnosisAgent` Protocol from spec 09; Managed Agents can swap in later without touching HTTP callers.

## User-facing behavior

No direct UI in this spec. The calling surface is one HTTP endpoint:

1. After photos have been uploaded (spec 11) and segmented (spec 12), the frontend calls `POST /diagnosis/run` with `{measurement_id, photo_ids}`.
2. The backend loads each segmented crop, base64-encodes it, fans out to three specialist agents concurrently, collects their JSON outputs, hands them to the coordinator, and returns a single `DiagnosisResult`.
3. On partial specialist failure (one agent errors), the coordinator runs with the remaining survivors — the diagnosis degrades, it does not fail.
4. On total failure (all specialists error, or coordinator errors), a clear HTTP error is returned.

## Inputs and outputs

### Protocol widening — `backend/lib/diagnosis/agent.py`

Spec 09 explicitly permits widening `DiagnosisAgent.run()`. No ADR required.

```python
class DiagnosisAgent(Protocol):
    def run(
        self,
        prompt_name: str,
        variables: dict[str, str],
        images: list[bytes] | None = None,
        max_tokens: int = 256,
    ) -> AgentResponse: ...
```

`AnthropicAgent` implements the new args: images are attached as `type: "image"` content blocks (base64) alongside the text block.

### New module — `backend/lib/diagnosis/multi_agent.py`

```python
@dataclass(frozen=True)
class Issue:
    issue_type: str          # open string in v1
    confidence: float        # 0.0–1.0
    description: str
    recommended_adjustment: str

@dataclass(frozen=True)
class SpecialistDiagnosis:
    region: Literal["bust", "waist_hip", "back"]
    issues: list[Issue]

@dataclass(frozen=True)
class DiagnosisResult:
    issues: list[Issue]
    primary_recommendation: str
    cascade_type: Literal["fba", "swayback", "none"]

async def run_diagnosis(
    images: list[bytes],
    agent_factory: Callable[[], DiagnosisAgent],
) -> DiagnosisResult: ...
```

- Three specialists run via `asyncio.gather(asyncio.to_thread(agent.run, ...), ...)`.
- Each specialist's `AgentResponse.text` is parsed as JSON into `SpecialistDiagnosis`. Parsing lives in `multi_agent.py`, never in `AnthropicAgent`.
- Coordinator receives surviving specialist diagnoses as `{{specialist_outputs}}` JSON string and returns `DiagnosisResult`.
- Partial failure: one specialist fails → coordinator runs with survivors + warning logged. All fail → `AllSpecialistsFailedError`.

### HTTP endpoint — `POST /diagnosis/run`

New `backend/routes/diagnosis.py` router.

#### Request body
- `measurement_id: str` — must match an existing measurement session.
- `photo_ids: list[str]` (1–3) — must correspond to segmented photos under that session.

#### Response body (200)
- `issues: list[Issue]`
- `primary_recommendation: str`
- `cascade_type: "fba" | "swayback" | "none"`

#### Errors
- **422** — empty `photo_ids`, > 3 `photo_ids`, or empty `measurement_id`.
- **404** — unknown `measurement_id` or any `photo_id` has no segmented crop → `{"detail": "Photo not found"}`.
- **500** — `ANTHROPIC_API_KEY` missing → `{"detail": "ANTHROPIC_API_KEY not configured"}`.
- **502** — all specialists failed or coordinator error → `{"detail": "Diagnosis service error"}`.

### Prompt files

- `prompts/diagnosis/bust/v1_baseline.md` — bust-region fit theory; instructs Claude to return **only** JSON matching `SpecialistDiagnosis`.
- `prompts/diagnosis/waist_hip/v1_baseline.md` — waist/hip theory; same output contract.
- `prompts/diagnosis/back/v1_baseline.md` — back theory (swayback pooling, shoulder blade gap); same contract.
- `prompts/diagnosis/coordinator/v1_baseline.md` — receives `{{specialist_outputs}}`; returns **only** JSON matching `DiagnosisResult`; enumerates closed set `cascade_type ∈ {"fba","swayback","none"}`.

## Acceptance criteria

- [ ] Given `AnthropicAgent` called with `images=[bytes1, bytes2]`, the Anthropic SDK call includes two `type: "image"` content blocks with base64-encoded data.
- [ ] Given `AnthropicAgent` called with `max_tokens=4096`, `messages.create(...)` is called with `max_tokens=4096`.
- [ ] Existing hello-world callsite (`run("hello_world", {"name": "Steph"})` with no `images`) continues to pass — no spec 09 regressions.
- [ ] Given valid JSON matching `SpecialistDiagnosis`, `_parse_specialist(region, text)` returns a correctly populated dataclass with `confidence` clamped to `[0.0, 1.0]`.
- [ ] Given malformed JSON or missing required fields, `_parse_specialist` raises `SpecialistParseError` with the offending text in the message.
- [ ] Given three successful specialists, the coordinator prompt is rendered with all three serialised in `{{specialist_outputs}}`.
- [ ] Given three mocked specialists each with 100 ms delay, `run_diagnosis` completes in < 200 ms (proves concurrency).
- [ ] Given one specialist fails and two succeed, the coordinator runs with the two survivors and a warning is logged naming the failed region.
- [ ] Given all three specialists fail, `AllSpecialistsFailedError` is raised.
- [ ] Given coordinator returns `cascade_type: "banana"`, `CoordinatorParseError` is raised.
- [ ] Given valid request with `get_agent` patched to return canned outputs, `POST /diagnosis/run` returns 200 with `DiagnosisResult` shape.
- [ ] Unknown `measurement_id` → 404 with `detail="Photo not found"`.
- [ ] `photo_id` with no segmented crop → 404 with `detail="Photo not found"`.
- [ ] `ANTHROPIC_API_KEY` unset → 500 with `detail="ANTHROPIC_API_KEY not configured"`.
- [ ] `AllSpecialistsFailedError` raised → 502 with `detail="Diagnosis service error"`.
- [ ] `photo_ids=[]` or length > 3 → 422.
- [ ] `backend/lib/diagnosis/` (including `multi_agent.py`) has no `fastapi` imports (import-hygiene test extended).
- [ ] Live smoke test `@pytest.mark.integration` — when `ANTHROPIC_API_KEY` set, runs full pipeline against a fixture segmented crop and asserts `cascade_type ∈ {"fba","swayback","none"}`. Skipped otherwise.
- [ ] `uv run pytest` passes; `uv run ruff check . && uv run black --check .` exit 0.

## Out of scope

- Photo annotation overlay UI — separate spec.
- Managed Agents SDK — direct SDK only; Protocol preserves swap-in later.
- Retry/backoff on Anthropic errors — fail fast per specialist, degrade gracefully.
- Streaming coordinator output.
- Caching diagnoses.
- Using measurement values inside prompts (v1: `measurement_id` is session-correlation only).
- Self-iterating fitting loop (V2 stretch).
- Fourth/fifth specialist (shoulder, sleeve).
- Cost/token budget enforcement.

## Technical approach

- **Async orchestration:** `asyncio.gather(asyncio.to_thread(agent.run, ...), ...)`. FastAPI handler is `async def`.
- **Base64 once:** orchestrator encodes each image once and passes `list[bytes]` to all specialists.
- **JSON parsing isolated:** `multi_agent.py` owns parsing; `AnthropicAgent.AgentResponse.text` remains an opaque string.
- **Partial failure:** individual specialist failures caught, logged, excluded from coordinator input. Only total failure bubbles to 502.
- **Closed-set validation:** coordinator prompt enumerates allowed `cascade_type` values; parser re-validates server-side.
- **Route thinness:** `routes/diagnosis.py` resolves photo paths, reads bytes, constructs agent via `get_agent()` factory, awaits `run_diagnosis`, maps exceptions to HTTP codes.

## Dependencies

- External libraries: none new — `anthropic` already present (spec 09). Stdlib: `asyncio`, `base64`, `json`.
- Specs first: 09 (Protocol + `AnthropicAgent`), 11 (photo storage + `resolve_photo_path`), 12 (segmentation, provides `cropped_path`).
- External services: Anthropic API (`ANTHROPIC_API_KEY`).

## Testing approach

- **Unit tests** in `backend/tests/test_multi_agent_parse.py` — parsing happy path, malformed JSON, bad `cascade_type`.
- **Unit tests** in `backend/tests/test_multi_agent_orchestration.py` — happy path, timing assertion, one-fail degradation, all-fail, coordinator-fail.
- **Agent widening tests** — extend `backend/tests/test_hello_agent.py`: new args forwarded to SDK; zero-image callsite still works.
- **Route tests** in `backend/tests/test_routes_diagnosis.py` — 200 / 404 / 422 / 500 / 502 with `get_agent` patched.
- **Import-hygiene test** extended to cover `multi_agent.py`.
- **Live integration test** (`@pytest.mark.integration`) — fixture segmented crop at `backend/tests/fixtures/diagnosis/sample_front.png`.
- **Manual verification:** upload → segment → `POST /diagnosis/run` — eyeball `DiagnosisResult` against a known fit issue.

## Open questions

1. **`issue_type` closed enum vs open string** — recommended default: open string in v1. Tighten to enum in V2 once cascade router is written.
2. **`measurement_id` in prompts** — recommended default: session-correlation only in v1; prompts reason from photos alone.
3. **Coordinator sees photos or only JSON** — recommended default: JSON only. Keeps synthesis cheap and focused.
4. **`max_tokens` budget** — recommended default: 1024 per specialist and coordinator. Revisit if truncation occurs in eval.

## Notes for implementer

- Write failing tests first per `CLAUDE.md` rule 5. Start at `_parse_specialist`, then orchestrator with mocked agents, then widened `AnthropicAgent`, then the route.
- Never hardcode prompt strings — all four prompts in `prompts/diagnosis/*/v1_baseline.md`.
- `backend/lib/diagnosis/` import-hygiene invariant is load-bearing — add `multi_agent.py` to the existing test.
- Use `asyncio.to_thread` for the sync Anthropic SDK — don't rewrite as async.
- Base64-encode each image exactly once in the orchestrator.
- If coordinator returns `cascade_type` outside the closed set, treat as parse error (502), never silently coerce to `"none"`.
- Fixture segmented crop for integration test: use a photo staged to reliably trigger one cascade type.
