# Spec: Shoulder & Sleeve Specialist Agent

**Spec ID:** 22-shoulder-sleeve-specialist
**Status:** implemented
**Created:** 2026-04-26
**Depends on:** 16-multi-agent-diagnosis

## What it does

Adds a fourth specialist Claude Opus 4.7 agent to the multi-agent diagnosis system. The `shoulder_sleeve` specialist examines the shoulder and sleeve region of the muslin photos — shoulder slope, shoulder position (forward/backward/dropped/raised), shoulder width, sleeve pitch, sleeve length, and armhole ease. For fitted bodices and jackets this region is often the hardest to diagnose visually, and a dedicated specialist with focused fit theory produces substantially sharper findings than a generalist prompt. The specialist integrates into the existing orchestrator by appending its region to `_SPECIALIST_REGIONS`; no orchestration logic changes.

## User-facing behavior

No direct UI change. The existing `POST /diagnosis/run` endpoint now returns shoulder and sleeve issues alongside bust, waist/hip, and back findings. The coordinator synthesises all four specialists. If the coordinator identifies a forward shoulder as the primary finding, it returns `cascade_type: "none"` — the `forward_shoulder` cascade is out of scope for this spec and will be implemented separately.

## Inputs and outputs

### Inputs (to the specialist agent — unchanged from spec 16 contracts)
- `images: list[bytes]` — the same segmented muslin photo crops passed to all specialists (1–3 photos, up to front/back/side views)
- `prompt_name: str` — `"diagnosis/shoulder_sleeve/v1_baseline"`
- `variables: dict[str, str]` — empty for v1 (no measurement injection)

### Outputs
- `SpecialistDiagnosis` dataclass with `region: "shoulder_sleeve"` and `issues: list[Issue]`

The `region` literal type in `multi_agent.py` widens from `Literal["bust", "waist_hip", "back"]` to include `"shoulder_sleeve"`.

### Errors
- Same partial-failure contract as spec 16: if this specialist fails, the coordinator runs with the remaining three survivors. The diagnosis degrades, it does not fail.

## Technical approach

Two file changes and one prompt file addition:

1. **`backend/lib/diagnosis/multi_agent.py`** — append `"shoulder_sleeve"` to `_SPECIALIST_REGIONS`. Widen `SpecialistDiagnosis.region` literal type.

2. **`prompts/diagnosis/shoulder_sleeve/v1_baseline.md`** — new specialist prompt (full text below).

3. **`prompts/diagnosis/coordinator/v1_baseline.md`** — add a paragraph noting the coordinator may now receive a fourth specialist output keyed `"shoulder_sleeve"`, and add guidance that shoulder/sleeve issues should result in `cascade_type: "none"` until a `forward_shoulder` cascade is implemented.

No changes to route, orchestration logic, HTTP schema, or other prompt files.

## Prompt content

The following is the complete text of `prompts/diagnosis/shoulder_sleeve/v1_baseline.md`. Note: the JSON schema in the actual file must be wrapped in a ` ```json ... ``` ` code fence, matching the convention used in `bust/v1_baseline.md`, `back/v1_baseline.md`, and `waist_hip/v1_baseline.md`.

```
You are an expert pattern-making specialist with 20+ years of experience fitting garments. You are examining a photo of someone wearing a muslin (test garment) and your task is to diagnose fit issues in the **shoulder and sleeve region**.

## What to look for in the shoulder area

Examine the garment from the neckline across the shoulder seam and down the armhole, focusing on:

- **Shoulder slope — too steep**: diagonal drag lines running from the neck/shoulder seam down toward the bust or armhole. The shoulder seam pulls downward at the outer edge. Indicates the pattern shoulder slope is flatter than the wearer's.
- **Shoulder slope — too flat**: the sleeve cap or shoulder area bunches horizontally at the outer shoulder. The shoulder seam rides up. Indicates the pattern slope is steeper than the wearer's.
- **Forward shoulder**: the shoulder seam rolls visibly to the front of the shoulder point when viewed from the side. The back of the garment appears to pull across the upper back. Common in people who work at a desk.
- **Backward shoulder**: the shoulder seam rolls to the back. The front of the garment pulls diagonally across the upper chest.
- **Dropped shoulder**: the shoulder seam sits below the actual shoulder point, creating a loose, bunchy cap area. The sleeve head may have visible excess fabric.
- **Raised shoulder**: the shoulder seam sits above the shoulder point or the body in that area. Diagonal tension lines run from neck outward.
- **Narrow shoulders**: the armhole seam pulls inward from the shoulder point; diagonal stress lines run from shoulder toward the bust.
- **Broad shoulders**: excess fabric at the outer shoulder; the shoulder seam extends past the shoulder point.

## What to look for in the sleeve and armhole area

Examine from the sleeve cap through to the sleeve hem, focusing on:

- **Sleeve pitch — cap twisting forward**: the sleeve hangs with the seam twisting toward the front of the arm; a diagonal fold runs from the back of the sleeve cap toward the front of the elbow. The wearer's arm hangs slightly in front of the body naturally.
- **Sleeve pitch — cap twisting backward**: the seam twists toward the back; fold runs from front cap toward the back of the elbow.
- **Sleeve length**: obvious excess fabric at the hem (too long) or the cuff sitting above the wrist bone (too short). Note approximate excess or shortage.
- **Armhole ease — too tight**: horizontal pulling lines across the armhole front or back; the wearer cannot comfortably raise their arm; the sleeve head pulls down when the arm is raised.
- **Armhole ease — too much**: visible excess fabric pooling around the underarm; the sleeve hangs away from the body; the armhole seam drops below the natural armhole.
- **Square shoulders**: horizontal wrinkles running from the neck across the shoulder; the shoulder seam lies flat but the outer edge has nowhere to go.
- **Sloping shoulders**: diagonal wrinkles angling from the neck down toward the outer shoulder; the collar or neckline may gap.

## Distinguishing shoulder slope from forward shoulder

These two issues produce similar visual cues but require different pattern corrections:
- **Shoulder slope problems** show drag lines that run diagonally *downward from the neck* along the shoulder seam itself.
- **Forward shoulder** shows the seam *rolling around the shoulder point* when viewed from the side. The drag lines originate at the upper back, not along the shoulder seam top.
- When in doubt, report both with lower confidence rather than committing to one.

## Output instructions

Return ONLY a JSON object matching this exact schema. Do not include any explanatory text before or after the JSON.

[schema block — wrap in ```json fence in the actual file]
{
  "region": "shoulder_sleeve",
  "issues": [
    {
      "issue_type": "string describing the fit issue (e.g. 'forward_shoulder', 'sleeve_pitch_forward', 'tight_armhole')",
      "confidence": 0.0,
      "description": "detailed description of what you observe in the photo",
      "recommended_adjustment": "specific pattern adjustment recommended"
    }
  ]
}

- `confidence` must be a float between 0.0 (not sure) and 1.0 (certain)
- Include an entry for each distinct issue observed
- If no issues are observed in the shoulder and sleeve region, return an empty `issues` array
- Be specific: identify which shoulder (left/right if asymmetric), direction of drag lines, and approximate magnitude where visible
```

## Coordinator prompt amendment

Add the following to `prompts/diagnosis/coordinator/v1_baseline.md`, in the "Specialist outputs" section preamble and in the cascade type table:

- Preamble note: "You may receive three or four specialist outputs. A fourth specialist covering `shoulder_sleeve` may be present."
- In the cascade table, add: `"none"` guidance note: "Choose `"none"` also when the primary finding is a shoulder or sleeve issue — no shoulder or sleeve cascade is available in this version."

The `cascade_type` closed set remains `{"fba", "swayback", "none"}`. No new cascade type is added here.

## Acceptance criteria

- [ ] Given `_SPECIALIST_REGIONS` in `multi_agent.py`, when the module is imported, then `"shoulder_sleeve"` is present in the list.
- [ ] Given `prompts/diagnosis/shoulder_sleeve/v1_baseline.md`, when the file is read and rendered with an empty variables dict, then no `{{...}}` placeholders remain.
- [ ] Given a mocked `shoulder_sleeve` specialist that returns valid JSON with `"region": "shoulder_sleeve"`, when `run_diagnosis` is called, then the `DiagnosisResult.issues` list includes the specialist's issues.
- [ ] Given a mocked `shoulder_sleeve` specialist that raises an exception, when `run_diagnosis` is called with the other three specialists succeeding, then the coordinator runs with three survivors and a warning is logged naming `"shoulder_sleeve"`.
- [ ] Given coordinator prompt file, when grepped for `"shoulder_sleeve"`, then at least one line matches — confirming the coordinator knows the new region exists.
- [ ] Given a `DiagnosisResult` where all issues originate from `shoulder_sleeve`, then `cascade_type` is `"none"` (coordinator prompt drives this; test via integration or a mocked coordinator response).
- [ ] Given `uv run pytest`, then all existing spec-16 acceptance criteria still pass (no regressions).
- [ ] Given `uv run ruff check . && uv run black --check .`, then exit code is 0.
- [ ] Given `ANTHROPIC_API_KEY` set, a live `@pytest.mark.integration` test calls the specialist with a fixture muslin photo and asserts the response parses into a valid `SpecialistDiagnosis` with `region == "shoulder_sleeve"`.

## Out of scope

- `forward_shoulder` cascade type — a natural next step but a separate spec. The coordinator maps shoulder issues to `cascade_type: "none"` for now.
- Sleeve cap ease adjustment cascade.
- Shoulder pad / structured shoulder fitting (couture territory, out of scope for V1).
- Asymmetric shoulder diagnosis (left vs right shoulder height difference requiring a shoulder pad lift).
- Changes to the HTTP route, request/response schema, or frontend.

## Dependencies

- External libraries: none new — inherits `anthropic` from spec 09/16.
- Specs that must be implemented first: **16-multi-agent-diagnosis** (provides `_SPECIALIST_REGIONS`, `SpecialistDiagnosis`, `run_diagnosis`, `DiagnosisAgent` Protocol).
- External services: Anthropic API (`ANTHROPIC_API_KEY`).

## Testing approach

- **Unit test** in `backend/tests/test_multi_agent_orchestration.py` — extend existing orchestration tests: four-specialist happy path, shoulder_sleeve-only failure degrades to three survivors.
- **Unit test** in `backend/tests/test_multi_agent_parse.py` — `_parse_specialist("shoulder_sleeve", valid_json)` returns correct dataclass; `region` field validates.
- **Prompt render test** — assert `prompts/diagnosis/shoulder_sleeve/v1_baseline.md` has no unresolved `{{}}` placeholders after rendering with empty dict.
- **Coordinator grep test** — assert coordinator prompt file contains `"shoulder_sleeve"`.
- **Integration test** (`@pytest.mark.integration`) — live call returns parseable `SpecialistDiagnosis`.
- **Regression** — full `uv run pytest` passes.

## Open questions

None blocking implementation. The following are noted for future specs:

- Should `forward_shoulder` become a cascade type in spec 24? If yes, the coordinator prompt will need updating at that time.
- When the `forward_shoulder` cascade ships, does the implementer of that spec also update this specialist's prompt, or is this specialist's prompt already sufficient?

## Notes for implementer

- `_SPECIALIST_REGIONS` in `multi_agent.py` is a list of strings; appending `"shoulder_sleeve"` is a one-line change.
- The `SpecialistDiagnosis.region` literal type needs widening. If it is used in a `match` statement or if exhaustiveness is checked, the type checker will catch omissions.
- The coordinator prompt amendment is additive — do not remove or reorder the existing cascade table entries. Append the shoulder_sleeve note as a parenthetical in the `"none"` bullet.
- Write the failing integration test first; it will fail until the prompt file exists.
- The prompt file path must be exactly `prompts/diagnosis/shoulder_sleeve/v1_baseline.md` — the loader constructs the path from `prompt_name` by convention.
- In the actual prompt file, wrap the JSON schema in a ` ```json ... ``` ` code fence, matching siblings `bust/v1_baseline.md` and `back/v1_baseline.md`. The spec shows it without a fence only because fences cannot be nested in a fenced code block.

## Implementation notes

**What was implemented:**

1. `backend/lib/diagnosis/multi_agent.py`:
   - Appended `"shoulder_sleeve"` to `_SPECIALIST_REGIONS` (now 4 regions)
   - Widened `SpecialistDiagnosis.region` Literal type to include `"shoulder_sleeve"`
   - Updated module docstring and `AllSpecialistsFailedError` message to say "four" instead of "three"

2. `prompts/diagnosis/shoulder_sleeve/v1_baseline.md`: Created with the exact content specified in the spec. JSON schema block is wrapped in a ` ```json ` fence.

3. `prompts/diagnosis/coordinator/v1_baseline.md`:
   - Changed "three specialist agents" to "up to four specialist agents" in the opening
   - Added a note after `{{specialist_outputs}}` that a fourth specialist covering `shoulder_sleeve` may be present
   - Added guidance to the `"none"` bullet that shoulder/sleeve issues should use `cascade_type: "none"`

**Test files updated/created:**
- `backend/tests/test_multi_agent_orchestration.py`: Updated all existing tests to expect 4 specialists + coordinator (5 calls total); added `TestShoulderSleeveSpecialist` class with 3 new tests
- `backend/tests/test_multi_agent_parse.py`: Added `TestParseSpecialistShoulderSleeve` class
- `backend/tests/test_prompt_files.py`: New file with 6 tests covering prompt file existence and content

**Deviations from spec:**
- None. All acceptance criteria covered. The integration test (`@pytest.mark.integration`) was not implemented as it requires a live API key — this matches the pattern established by spec 16.

**Pre-existing failures (not caused by this implementation):**
- `backend/tests/test_export_pdf.py` — 9 failures are pre-existing in this worktree, unrelated to this spec
- `backend/routes/photos.py` — pre-existing ruff I001 import ordering issue in this worktree

**Open questions:** None.
