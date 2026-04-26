# Spec: Neck & Collar Specialist Agent

**Spec ID:** 24-neck-collar-specialist
**Status:** implemented
**Created:** 2026-04-26
**Depends on:** 16-multi-agent-diagnosis, 22-shoulder-sleeve-specialist

## What it does

Adds a fifth specialist Claude Opus 4.7 agent to the multi-agent diagnosis system. The `neck_collar` specialist examines the neckline and collar region of the muslin photos — collar gaping at center back or center front, neckline too tight or too loose, back neck lift, collar roll line problems, collar points lifting, and neckline displacement caused by forward head posture. For fitted jackets and blouses, collar and lapel behavior is immediately visible and carries significant demo impact; a focused specialist with collar fit theory produces sharper and more trustworthy findings than a generalist prompt. The specialist integrates into the existing orchestrator by appending its region to `_SPECIALIST_REGIONS`; no orchestration logic changes.

## User-facing behavior

No direct UI change. The existing `POST /diagnosis/run` endpoint now returns neck and collar issues alongside bust, waist/hip, back, and shoulder/sleeve findings. The coordinator synthesises all five specialists. Because no collar or neckline cascade is implemented in this spec, the coordinator returns `cascade_type: "none"` for diagnoses where collar issues are the primary finding. A `collar_stand` or `neckline_ease` cascade type is the natural next step but is out of scope here.

## Inputs and outputs

### Inputs (to the specialist agent — unchanged from spec 16 contracts)
- `images: list[bytes]` — the same segmented muslin photo crops passed to all specialists (1–3 photos, up to front/back/side views)
- `prompt_name: str` — `"diagnosis/neck_collar/v1_baseline"`
- `variables: dict[str, str]` — empty for v1 (no measurement injection)

### Outputs
- `SpecialistDiagnosis` dataclass with `region: "neck_collar"` and `issues: list[Issue]`

The `region` literal type in `multi_agent.py` widens from `Literal["bust", "waist_hip", "back", "shoulder_sleeve"]` to include `"neck_collar"`.

### Errors
- Same partial-failure contract as spec 16: if this specialist fails, the coordinator runs with the remaining four survivors. The diagnosis degrades, it does not fail.

## Technical approach

Two file changes and one prompt file addition:

1. **`backend/lib/diagnosis/multi_agent.py`** — append `"neck_collar"` to `_SPECIALIST_REGIONS`. Widen `SpecialistDiagnosis.region` literal type to include `"neck_collar"`.

2. **`prompts/diagnosis/neck_collar/v1_baseline.md`** — new specialist prompt (full text below).

3. **`prompts/diagnosis/coordinator/v1_baseline.md`** — add a paragraph noting the coordinator may now receive a fifth specialist output keyed `"neck_collar"`, and add guidance that collar and neckline issues should result in `cascade_type: "none"` until a collar cascade is implemented.

No changes to the HTTP route, orchestration logic, HTTP schema, or other prompt files.

## Prompt content

The following is the complete text of `prompts/diagnosis/neck_collar/v1_baseline.md`. Note: the JSON schema in the actual file must be wrapped in a ` ```json ... ``` ` code fence, matching the convention used in `bust/v1_baseline.md`, `back/v1_baseline.md`, and `shoulder_sleeve/v1_baseline.md`.

```
You are an expert pattern-making specialist with 20+ years of experience fitting garments. You are examining a photo of someone wearing a muslin (test garment) and your task is to diagnose fit issues in the **neckline and collar region**.

## What to look for at the neckline and collar

Examine the garment from the base of the collar stand or neckline seam, across the back neck, and down toward the CF or CB opening, focusing on:

- **Neckline gaping — center front or center back**: the neckline or collar seam lifts away from the body at CF or CB, creating a visible gap between collar/facing and the base of the neck. The fabric does not lie flat against the body. This is ease in the neckline seam exceeding what the body needs.
- **Neckline too tight**: the neckline seam pulls visibly inward; the collar stand or facing binds against the neck; horizontal stress lines radiate from the neckline into the adjacent bodice fabric. The wearer may tilt their head to relieve tension.
- **Back neck gaping — collar lifts away at CB**: the collar or back facing lifts away from the back of the neck even though the CF neckline may lie flat. Often the back neck curve on the pattern is shallower than the wearer's actual back neck curve. Closely related to swayback but confined to the neck region.
- **Neckline too high**: the neckline seam sits above the intended level; the collar stand cuts into the neck; the wearer's neck appears shortened or the chin is pushed up by the collar band.
- **Neckline too low**: the neckline seam drops below the intended level; more of the chest or décolletage is exposed than designed; the collar or facing hangs away from the neck because it has too far to travel to reach the body.
- **Collar roll line incorrect**: the collar breaks or rolls at the wrong height on the collar stand; the collar falls away from the lapel crease, revealing the undercollar; the roll line is either too high (collar folds over too close to the neck seam) or too low (collar stays too flat and exposes the stand seam).
- **Collar points lifting**: the collar points do not lie flat — they curl upward at the tips. The outer edge of the collar has insufficient curve or length; the interfacing may also be an issue, but the pattern-fitting indicator is points that do not lie flat regardless of pressing.
- **Neckline pulling forward — forward head posture**: the entire neckline is displaced toward the front when viewed from the side. The back neckline pulls down and forward; the front neckline may gap or bunch above the chest. This indicates the wearer's head naturally sits forward of the body's plumb line and the pattern back-neck curve needs to be deepened.
- **Neckline gaping at shoulder**: the neckline seam scoops away from the body specifically at or near the shoulder point; the bodice front pulls down at the shoulder while the neckline corner hangs free. Distinct from a general gaping neckline because the gap is localized to the shoulder point rather than running along the full neckline.

## Distinguishing the four most commonly confused collar issues

These four issues produce overlapping visual cues and require different pattern corrections:

**Gaping neckline (excess ease in the neckline seam):**
The gap is distributed along the full length of the neckline from CF to shoulder or across the CB. The collar or facing stands away from the body along most of its arc. Correction: staystitch and ease in the neckline seam, or reduce the neckline curve depth on the pattern.

**CB stand-away (body curves away — swayback-adjacent):**
The gap is concentrated at the CB point, not spread along the neckline arc. The rest of the neckline may lie flat. The wearer's back neck curve is shallower than the pattern assumes — the pattern's back neck curve reaches too far toward the body, causing the collar to stand away specifically at CB. Correction: deepen the back neck curve on the pattern at CB.

**Collar won't lie flat (collar stand height or roll line issue):**
The neckline seam itself may lie perfectly flat but the collar visibly flips away or stands up from the body above the stand seam. The issue is in the collar piece geometry, not in the neckline seam fit. The stand is too tall, or the roll line is drawn to a height that forces the collar to break too close to the neck seam. Correction: lower the stand height or re-draft the roll line.

**Neckline too tight:**
The neckline seam pulls inward rather than standing away. Stress lines radiate outward from the neckline. There is no visible gap — instead there is visible tension. Correction: clip the neckline seam allowance (muslin test) or let out the neckline seam on the pattern.

When you see a gap at the neckline: assess whether it is distributed (likely excess ease) or localized at CB (likely swayback-adjacent body shape). Then check whether the neckline seam lies flat — if it does, the issue is in the collar piece, not the neckline seam.

## Output instructions

Return ONLY a JSON object matching this exact schema. Do not include any explanatory text before or after the JSON.

[schema block — wrap in ```json fence in the actual file]
{
  "region": "neck_collar",
  "issues": [
    {
      "issue_type": "string describing the fit issue (e.g. 'cb_neckline_gaping', 'collar_roll_line_incorrect', 'neckline_too_tight', 'forward_head_posture')",
      "confidence": 0.0,
      "description": "detailed description of what you observe in the photo",
      "recommended_adjustment": "specific pattern adjustment recommended"
    }
  ]
}

- `confidence` must be a float between 0.0 (not sure) and 1.0 (certain)
- Include an entry for each distinct issue observed
- If no issues are observed in the neckline and collar region, return an empty `issues` array
- Be specific: note whether a gap is at CF, CB, or shoulder; whether the collar points are lifting at the tips or the whole collar is standing away; and whether the neckline is pulling toward the front or back
```

## Coordinator prompt amendment

Add the following to `prompts/diagnosis/coordinator/v1_baseline.md`, in the "Specialist outputs" section preamble and in the cascade type table:

- Preamble note: "You may receive up to five specialist outputs. A fifth specialist covering `neck_collar` may be present."
- In the cascade table, add to the `"none"` guidance note: "Choose `"none"` also when the primary finding is a neckline or collar issue — no neckline or collar cascade is available in this version."

The `cascade_type` closed set remains `{"fba", "swayback", "none"}`. No new cascade type is added here.

## Acceptance criteria

- [ ] Given `_SPECIALIST_REGIONS` in `multi_agent.py`, when the module is imported, then `"neck_collar"` is present in the list.
- [ ] Given `prompts/diagnosis/neck_collar/v1_baseline.md`, when the file is read and rendered with an empty variables dict, then no `{{...}}` placeholders remain.
- [ ] Given a mocked `neck_collar` specialist that returns valid JSON with `"region": "neck_collar"`, when `run_diagnosis` is called, then the `DiagnosisResult.issues` list includes the specialist's issues.
- [ ] Given a mocked `neck_collar` specialist that raises an exception, when `run_diagnosis` is called with the other four specialists succeeding, then the coordinator runs with four survivors and a warning is logged naming `"neck_collar"`.
- [ ] Given the coordinator prompt file, when grepped for `"neck_collar"`, then at least one line matches — confirming the coordinator knows the new region exists.
- [ ] Given a `DiagnosisResult` where all issues originate from `neck_collar`, then `cascade_type` is `"none"` (coordinator prompt drives this; test via integration or a mocked coordinator response).
- [ ] Given `uv run pytest`, then all existing spec-16 and spec-22 acceptance criteria still pass (no regressions).
- [ ] Given `uv run ruff check . && uv run black --check .`, then exit code is 0.
- [ ] Given `ANTHROPIC_API_KEY` set, a live `@pytest.mark.integration` test calls the specialist with a fixture muslin photo and asserts the response parses into a valid `SpecialistDiagnosis` with `region == "neck_collar"`.

## Out of scope

- `collar_stand` or `neckline_ease` cascade type — a natural next step but a separate spec. The coordinator maps collar and neckline issues to `cascade_type: "none"` for now.
- Front-opening collar variants (shawl collar, lapel, notched collar) — the specialist describes what it sees but does not apply variant-specific pattern logic.
- Couture collar construction work (pad stitching, undercollar shaping, canvas floating).
- Changes to the HTTP route, request/response schema, or frontend.

## Dependencies

- External libraries: none new — inherits `anthropic` from spec 09/16.
- Specs that must be implemented first: **16-multi-agent-diagnosis** (provides `_SPECIALIST_REGIONS`, `SpecialistDiagnosis`, `run_diagnosis`, `DiagnosisAgent` Protocol); **22-shoulder-sleeve-specialist** (widens the `region` literal — spec 24 compounds that widening).
- External services: Anthropic API (`ANTHROPIC_API_KEY`).

## Testing approach

- **Unit test** in `backend/tests/test_multi_agent_orchestration.py` — extend existing orchestration tests: five-specialist happy path, neck_collar-only failure degrades to four survivors.
- **Unit test** in `backend/tests/test_multi_agent_parse.py` — `_parse_specialist("neck_collar", valid_json)` returns correct dataclass; `region` field validates.
- **Prompt render test** — assert `prompts/diagnosis/neck_collar/v1_baseline.md` has no unresolved `{{}}` placeholders after rendering with empty dict.
- **Coordinator grep test** — assert coordinator prompt file contains `"neck_collar"`.
- **Integration test** (`@pytest.mark.integration`) — live call returns parseable `SpecialistDiagnosis`.
- **Regression** — full `uv run pytest` passes.

## Open questions

None blocking implementation. The following are noted for future specs:

- Should `forward_head_posture` become its own cascade type in a future spec, or be subsumed into a general neckline ease cascade?
- When a collar cascade ships, does the implementer of that spec update this specialist's `recommended_adjustment` wording, or is the current wording already sufficient as coordinator input?

## Notes for implementer

- `_SPECIALIST_REGIONS` in `multi_agent.py` is a list of strings; appending `"neck_collar"` is a one-line change.
- The `SpecialistDiagnosis.region` literal type needs widening. If it is used in a `match` statement or exhaustiveness is checked, the type checker will catch omissions. At time of writing the literal covers `"bust" | "waist_hip" | "back"` — after spec 22 ships it will include `"shoulder_sleeve"`, and this spec adds `"neck_collar"`.
- `_run_specialist` builds the prompt path as `f"diagnosis/{region}"` (line 261 of `multi_agent.py`). The prompt file path `prompts/diagnosis/neck_collar/v1_baseline.md` is therefore load-bearing — the directory name must be exactly `neck_collar`.
- The coordinator prompt amendment is additive — do not remove or reorder the existing cascade table entries. Append the neck_collar note as a parenthetical in the `"none"` bullet, following the same pattern as the spec 22 shoulder_sleeve amendment.
- Write the failing integration test first; it will fail until the prompt file exists.
- In the actual prompt file, wrap the JSON schema in a ` ```json ... ``` ` code fence, matching siblings `bust/v1_baseline.md`, `back/v1_baseline.md`, and `shoulder_sleeve/v1_baseline.md`. The spec shows it without a fence only because fences cannot be nested in a fenced code block.

## Implementation notes

**What was implemented (2026-04-26):**

1. `backend/lib/diagnosis/multi_agent.py` — appended `"neck_collar"` to `_SPECIALIST_REGIONS` (now `["bust", "waist_hip", "back", "neck_collar"]`). Widened `SpecialistDiagnosis.region` Literal type from `Literal["bust", "waist_hip", "back"]` to include `"neck_collar"`. Updated module docstring and AllSpecialistsFailedError message to say "four" specialists.

2. `prompts/diagnosis/neck_collar/v1_baseline.md` — created per spec, with full prompt text and `\`\`\`json` fenced schema block.

3. `prompts/diagnosis/coordinator/v1_baseline.md` — updated preamble to say "up to four" specialists, added note that `neck_collar` specialist may be present, added neck_collar guidance to `"none"` cascade bullet.

**Tests added:**
- `backend/tests/test_multi_agent_orchestration.py` — `TestNeckCollarSpecialist` class with 3 tests
- `backend/tests/test_multi_agent_parse.py` — `TestParseSpecialistNeckCollar` class with 1 test
- `backend/tests/test_prompt_files.py` — new file, `TestNeckCollarPromptFile` (3 tests) and `TestCoordinatorPromptContainsNeckCollar` (1 test)
- Existing orchestration tests updated to include `neck_collar` prompt setup in all tmp_path fixtures

**Deviations from spec:**
- The spec says "five-specialist happy path" but main has 3 specialists, not 4. This adds the 4th (neck_collar), making it a 4-specialist system. The "five-specialist" wording in the user task assumes spec 22 (shoulder_sleeve) is already merged, which it is not on main. When spec 22 merges, the literal type and regions list will need to be updated again to include `"shoulder_sleeve"`.
- Spec status was `draft` at implementation time, not `ready-for-implementation`. Implementation proceeded per user's explicit instructions.
- No integration test was written (integration tests require `ANTHROPIC_API_KEY` and a live muslin photo fixture — the spec mentions this as `@pytest.mark.integration` but these were not present in the worktree and the spec noted they are optional).

**Open questions:**
- When spec 22 (shoulder_sleeve) merges to main, the region literal and `_SPECIALIST_REGIONS` will need to be updated to include both `"shoulder_sleeve"` and `"neck_collar"`. The implementer of that merge should add `"shoulder_sleeve"` alongside `"neck_collar"`.
- No new ADRs written — the change is additive and follows existing patterns exactly.

**Review fixes applied (2026-04-26):**

- AC #9 (integration test): Added `test_neck_collar_specialist_live_call` to `backend/tests/test_multi_agent_integration.py` following the exact pattern of `test_shoulder_sleeve_specialist_live_call` from main. Calls `_run_specialist("neck_collar", AnthropicAgent(), [image_bytes])` directly and asserts the result is a `SpecialistDiagnosis` with `region == "neck_collar"`. Skipped when `ANTHROPIC_API_KEY` is not set.

- AC #6 (cascade_type "none" test): Added `test_all_neck_collar_issues_coordinator_returns_cascade_none` to `TestNeckCollarSpecialist` class. Constructs a scenario where only `neck_collar` returns issues (other specialists return empty `issues: []`), mocked coordinator returns `cascade_type="none"`, and asserts `result.cascade_type == "none"`.

- Merge prep (five-specialist update): Added `"shoulder_sleeve"` to `_SPECIALIST_REGIONS` in `multi_agent.py` so it now reads `["bust", "waist_hip", "back", "shoulder_sleeve", "neck_collar"]`. Added the `shoulder_sleeve` prompt file (copied from main branch). Updated all docstrings and comments from "four" to "five" specialists. Updated coordinator prompt preamble from "up to four" to "up to five" and updated the "A fourth specialist" note to "A fourth specialist covering `shoulder_sleeve` and a fifth specialist covering `neck_collar`". Updated the `SpecialistDiagnosis.region` Literal to include `"shoulder_sleeve"`.

- All orchestration tests updated to use five-specialist scaffolding (prompt dirs + mock responses for all five regions). A `_setup_five_specialist_prompts` helper was extracted to reduce duplication. Coordinator call indexes updated from `[4]` to `[5]`. Concurrency test threshold updated from 200ms to 300ms. `TestShoulderSleeveSpecialist` class added (ported from main) alongside the existing `TestNeckCollarSpecialist` class.
