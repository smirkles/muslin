# Spec: Leg & Trouser Specialist Agent

**Spec ID:** 23-leg-specialist
**Status:** draft
**Created:** 2026-04-26
**Depends on:** 16-multi-agent-diagnosis

## What it does

Adds a fifth specialist Claude Opus 4.7 agent to the multi-agent diagnosis system. The `leg` specialist examines the leg and trouser region of the muslin photos — crotch length and curve, thigh ease, seat ease, trouser break at the hem, inner leg seam positioning, and knee/calf width. This specialist is partially blocked: the frontend currently shows "coming soon" for trouser patterns, and no trouser cascade exists. The specialist can be wired up and prompted now so that when the trouser pattern ships, diagnosis is ready immediately. For now the coordinator maps all leg-only findings to `cascade_type: "none"`.

## User-facing behavior

No direct UI change. When the user uploads muslin photos wearing trousers, `POST /diagnosis/run` will include leg/trouser issues in the returned `DiagnosisResult.issues` list. The `cascade_type` will be `"none"` for trouser-only sessions until a trouser cascade is implemented. Sessions without trouser photos will produce an empty issues array from this specialist (the model will see the bodice photos and correctly report no trouser-region issues).

## Inputs and outputs

### Inputs (to the specialist agent)
- `images: list[bytes]` — same segmented photo crops as all other specialists (1–3 photos)
- `prompt_name: str` — `"diagnosis/leg/v1_baseline"`
- `variables: dict[str, str]` — empty for v1

### Outputs
- `SpecialistDiagnosis` dataclass with `region: "leg"` and `issues: list[Issue]`

The `region` literal type in `multi_agent.py` widens to include `"leg"`.

### Errors
- Same partial-failure contract as spec 16 and 22: if the leg specialist fails, the coordinator runs with surviving specialists. The diagnosis degrades, it does not fail.

## Technical approach

Two file changes and one prompt file addition:

1. **`backend/lib/diagnosis/multi_agent.py`** — append `"leg"` to `_SPECIALIST_REGIONS`. Widen `SpecialistDiagnosis.region` literal type.

2. **`prompts/diagnosis/leg/v1_baseline.md`** — new specialist prompt (full text below).

3. **`prompts/diagnosis/coordinator/v1_baseline.md`** — add a note that a `leg` specialist may be present, and that leg-only findings should yield `cascade_type: "none"` until a trouser cascade is implemented.

No changes to route, orchestration logic, HTTP schema, or other prompt files.

## Prompt content

The following is the complete text of `prompts/diagnosis/leg/v1_baseline.md`. Note: the JSON schema in the actual file must be wrapped in a ` ```json ... ``` ` code fence, matching the convention used in sibling prompt files.

```
You are an expert pattern-making specialist with 20+ years of experience fitting garments. You are examining a photo of someone wearing a muslin (test garment) and your task is to diagnose fit issues in the **leg and trouser region**.

If the person in the photo is not wearing trousers or there is no visible leg/trouser region, return an empty issues array immediately — do not attempt to diagnose a skirt or bodice as trouser fit issues.

## What to look for in the crotch and seat area

Examine the back and front view from the waistband to mid-thigh, focusing on:

- **Crotch length — too short**: the fabric pulls horizontally across the crotch seam when the wearer stands naturally. The crotch seam may ride up. When the wearer sits or moves, the waistband pulls down at the back. Diagonal drag lines radiate from the crotch point.
- **Crotch length — too long**: excess fabric hangs below the crotch seam when standing; the crotch seam droops. There is a visible bubble or fold of fabric between the legs.
- **Crotch curve — too shallow**: pulling across the seat when the wearer bends forward; the back rise feels short even if the length measurement is correct. The fabric digs in at the seat.
- **Crotch curve — too deep**: excess fabric in the crotch area when standing; the inseam hangs low; the trousers sag at the seat even with correct length.
- **Seat ease — too tight**: horizontal pulling lines across the fullest part of the seat; the back pockets (if present) splay open; diagonal tension lines from the seat point toward the waist. Movement is restricted.
- **Seat ease — too much**: vertical folds or diagonal drag lines running from the waistband down toward the seat; excess fabric pooling at the back below the waistband.

## What to look for in the thigh and leg area

Examine from the crotch seam to the hem, focusing on:

- **Thigh ease — too tight**: horizontal pulling lines across the widest part of the thighs, most visible from the front; the inseam pulls toward the front; movement is restricted; the fabric strains when walking.
- **Thigh ease — too much**: vertical folds running down the outer thigh or inner thigh; the trouser leg hangs away from the body; the silhouette appears baggy when it should be fitted.
- **Inner leg seam positioning**: the inseam should hang straight down the center of the inner leg. If it swings toward the front, the crotch curve needs adjustment (more curve at front). If it swings toward the back, the back crotch seam needs to be deepened.
- **Knee width**: fabric pulling horizontally across the knee (too narrow) or vertical folds at the knee (too wide relative to the overall trouser leg width).
- **Calf width**: similar to knee — pulling indicates too narrow, vertical folds indicate too wide.
- **Trouser break at hem**: the hem should rest on the instep with the desired break. Note if the hem drags excessively (too long) or sits above the shoe entirely (too short). Identify the approximate excess or shortage.

## Distinguishing crotch length from crotch curve problems

These often present together but require different corrections:
- **Crotch length** problems affect the entire garment — too short and everything pulls upward; too long and everything droops.
- **Crotch curve** problems are localised to the seat and crotch area while the rest of the trouser length is correct.
- If pulling is concentrated at the seat/crotch but the break at the hem looks correct, suspect curve rather than length.

## Output instructions

Return ONLY a JSON object matching this exact schema. Do not include any explanatory text before or after the JSON.

[schema block — wrap in ```json fence in the actual file]
{
  "region": "leg",
  "issues": [
    {
      "issue_type": "string describing the fit issue (e.g. 'crotch_length_short', 'seat_ease_tight', 'thigh_ease_excess')",
      "confidence": 0.0,
      "description": "detailed description of what you observe in the photo",
      "recommended_adjustment": "specific pattern adjustment recommended"
    }
  ]
}

- `confidence` must be a float between 0.0 (not sure) and 1.0 (certain)
- Include an entry for each distinct issue observed
- If the person is not wearing trousers, or no issues are observed, return an empty `issues` array
- Be specific: identify front vs back, left vs right leg where relevant, and approximate magnitude (e.g. "approximately 1.5 inches too short in the crotch")
```

## Coordinator prompt amendment

Add the following to `prompts/diagnosis/coordinator/v1_baseline.md`:

- Preamble note: "You may receive up to five specialist outputs. A `leg` specialist may be present for trouser fittings."
- In the cascade table `"none"` bullet: "Choose `"none"` also when the primary finding is a leg or trouser issue — no trouser cascade is available in this version."

The `cascade_type` closed set remains `{"fba", "swayback", "none"}`.

## Future-work note: trouser cascade shapes

Documentation only — not implementation scope for this spec.

**`trouser_crotch`** — adjusts crotch length and/or curve. Operations: lengthen or shorten the crotch seam (translate seat point along the grain) and/or adjust the crotch curve control points. Steps: (1) mark the crotch seam, (2) measure adjustment amount, (3) slash at adjustment line, (4) spread or overlap, (5) true the inseam and outseam.

**`trouser_seat`** — adds or removes ease across the seat. Operations: vertical slash on the back trouser piece from waistband to crotch point, spread to add width or tuck to remove. Steps: (1) mark seat fullness line (typically 7–8 inches below waistband), (2) slash vertically, (3) spread or overlap, (4) true waistband, inseam, and outseam.

Both cascades will also need a garment-type field on the request so the leg specialist can be skipped for bodice sessions rather than relying on the model to self-identify.

## Acceptance criteria

- [ ] Given `_SPECIALIST_REGIONS` in `multi_agent.py`, when the module is imported, then `"leg"` is present in the list.
- [ ] Given `prompts/diagnosis/leg/v1_baseline.md`, when the file is read and rendered with an empty variables dict, then no `{{...}}` placeholders remain.
- [ ] Given a mocked `leg` specialist that returns valid JSON with `"region": "leg"`, when `run_diagnosis` is called, then `DiagnosisResult.issues` includes the specialist's issues.
- [ ] Given a mocked `leg` specialist that raises an exception, when `run_diagnosis` is called with other specialists succeeding, then the coordinator runs with survivors and a warning is logged naming `"leg"`.
- [ ] Given coordinator prompt file, when grepped for `"leg"`, then at least one line matches.
- [ ] Given a mocked coordinator that receives only leg issues, when `run_diagnosis` returns, then `cascade_type` is `"none"`.
- [ ] Given `uv run pytest`, then all existing spec-16 and spec-22 acceptance criteria still pass (no regressions).
- [ ] Given `uv run ruff check . && uv run black --check .`, then exit code is 0.
- [ ] Given `ANTHROPIC_API_KEY` set, a live `@pytest.mark.integration` test calls the specialist with a fixture bodice photo and asserts the response parses into a valid `SpecialistDiagnosis` with `region == "leg"` and `issues == []`.

## Out of scope

- `trouser_crotch` cascade type.
- `trouser_seat` cascade type.
- Garment-type filtering (skipping the leg specialist for bodice sessions). V1 relies on the model returning empty issues for non-trouser photos.
- Waistband fitting (rise height, waistband width).
- Inseam length adjustment cascade.
- Any frontend UI changes — the "coming soon" trouser pattern state is unchanged.

## Dependencies

- External libraries: none new.
- Specs that must be implemented first: **16-multi-agent-diagnosis**.
- Spec 22 (shoulder_sleeve) may be implemented in parallel — both specs touch `_SPECIALIST_REGIONS` and the coordinator prompt additively. Merge conflicts are trivial.
- External services: Anthropic API (`ANTHROPIC_API_KEY`).

## Testing approach

- **Unit test** in `backend/tests/test_multi_agent_orchestration.py` — five-specialist happy path; leg-only failure degrades gracefully.
- **Unit test** in `backend/tests/test_multi_agent_parse.py` — `_parse_specialist("leg", valid_json)` returns correct dataclass.
- **Prompt render test** — assert no unresolved `{{}}` in `prompts/diagnosis/leg/v1_baseline.md`.
- **Coordinator grep test** — assert coordinator prompt contains `"leg"`.
- **Leg-only cascade test** — mock coordinator returning only leg issues, assert `cascade_type == "none"`.
- **Integration test** (`@pytest.mark.integration`) — live call with bodice fixture returns `SpecialistDiagnosis` with `region == "leg"` and `issues == []`.
- **Regression** — full `uv run pytest` passes.

## Open questions

None blocking implementation. The following are noted for future specs:

- When trouser patterns ship in the frontend, should a garment-type field be added to `POST /diagnosis/run` so the orchestrator can skip the leg specialist for bodice sessions?
- Should `issue_type` values for leg issues be added to a closed enum at that point, or stay open strings (consistent with current V1 approach)?

## Notes for implementer

- This spec may be implemented in parallel with spec 22. If both are on the same branch, add both `"shoulder_sleeve"` and `"leg"` to `_SPECIALIST_REGIONS` in one commit and combine the coordinator prompt amendments into a single edit.
- The integration test passes correctly with empty `issues` — a bodice photo triggering no trouser findings is the expected and correct behavior.
- The prompt instructs the model to self-identify non-trouser photos and return empty issues — rely on this for V1 rather than implementing garment-type filtering in code.
- Prompt file path must be exactly `prompts/diagnosis/leg/v1_baseline.md`.
- In the actual prompt file, wrap the JSON schema in a ` ```json ... ``` ` code fence, matching sibling prompt files. The spec shows it without a fence only because fences cannot be nested inside a fenced code block.
