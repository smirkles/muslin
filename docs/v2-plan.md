# Project Plan v2 — "The Muslin Whisperer"

*(Working title — pick something better before pitching. Candidates: "Muslin", "Toile", "FitPath", "Adjust", or something with a sewing-pin / measuring-tape visual identity. TBD.)*

---

## At a Glance — For Anyone Picking This Up Cold

A web tool that helps home sewers adjust an existing sewing pattern to fit their actual body, by analyzing a photo of them wearing a muslin (test garment) of that pattern.

User uploads a sewing pattern + their measurements + photos of themselves in the muslin. The tool grades the pattern to their measurements as a baseline, then uses Claude Opus 4.7 (orchestrated as multiple specialist agents via Managed Agents) to diagnose remaining fit issues from the muslin photos and apply pattern adjustments — currently full bust adjustment (FBA) and swayback adjustment. Each adjustment cascade is animated step-by-step in 2D so the user sees and learns *why* each change is being made.

Built for Anthropic's "Built with Opus 4.7: a Claude Code hackathon" by Steph (Digital Smiles), April 2026. Solo build, 7 days.

---

## Strategic Positioning

**Hackathon problem statements addressed:**

*Problem 1 — Build From What You Know.* Steph is a home sewer with engineering chops. Pattern adjustment for fit is universally painful, gatekept knowledge passed down via YouTube and forum threads. The tool intercepts the moment every fitted sewer has had: standing in front of a mirror in a half-finished muslin, trying to figure out what's wrong.

*Problem 2 — Build For What's Next.* The product uses multi-agent Claude orchestration and a self-iterating fitting loop — workflows that only become possible with current Managed Agents capability. The cascade animation is "an interface that doesn't have a name yet" — neither pure CAD (which lets you change things but doesn't reason) nor pure tutorial (which explains things but doesn't apply them).

**The pitch line:**

> *"Every fitted sewing project starts with a muslin — a test garment in cheap fabric to check the fit before cutting your good fabric. Then you stand in front of the mirror trying to figure out why it pulls there, gapes here, bunches at the back. That's the moment a beginner gives up, an intermediate googles for an hour, and an expert friend would just glance over and say 'you need a swayback adjustment.' I built the expert friend."*

**Market evidence (to be filled in):** muslin/toile is established practice across millions of home sewers globally; FBA is the single most-Googled adjustment in home sewing; specialist indie pattern brands like Cashmerette have built entire businesses around fit-adjustment expertise — proof of willingness to pay. Full demand evidence gathering deferred to dedicated session.

---

## MVP Definition

### Must-have features (V1 = ship by Day 5)

1. **Pattern selection.** Users select from a small library of pre-loaded patterns (start with one: a fitted bodice or t-shirt). Pattern stored as structured SVG with named, addressable elements.

2. **Measurement input.** A form for bust, waist, hip, height, back length. Maps to SMPL body shape parameters. Grades the pattern to baseline size.

3. **Muslin photo upload.** User uploads 1–3 photos of themselves in the muslin (front, back, side). System segments the muslin from background using SAM 2.

4. **Multi-agent fit diagnosis.** Specialist Claude agents analyze different body regions in parallel via Managed Agents; coordinator synthesizes a diagnosis. Output: structured list of fit issues with confidence scores and recommended adjustments.

5. **Cascade adjustments — FBA and swayback.** Two adjustment types implemented end-to-end: full bust adjustment and swayback. Each runs as a deterministic geometric transform on the pattern SVG, orchestrated by Claude.

6. **2D cascade animation.** When an adjustment is applied, the SVG transforms animate step-by-step (using GSAP), with Claude-generated narration text appearing alongside each step. User sees the slash-and-spread, the dart rotation, the side seam truing as it happens, with explanations.

7. **Static 3D body view.** A Three.js viewer showing the SMPL body resized to user measurements. Rotatable, viewable from different angles. Garment NOT rendered on body in V1.

8. **Adjusted pattern download.** User can download the adjusted pattern as SVG or PDF.

### Stretch features (V2 = ship by Day 6 if time)

9. **Self-iterating fitting loop.** Managed Agent runs a loop: propose adjustment → simulate → evaluate against success criteria → propose next iteration. User reviews converged result rather than driving each step.

10. **Additional cascade types.** Lengthen/shorten bodice, broad shoulder adjustment, or sleeve cap adjustment.

11. **Override controls.** User can toggle off Claude's photo diagnosis, manually select fit issues from a checklist, or adjust the magnitude of any recommended adjustment.

12. **3D garment drape.** Static drape of adjusted garment on body using simple cloth simulation (Blender headless or Warp).

### Explicit non-goals

- Generating sewing patterns from scratch (no Sewformer-style prediction)
- Image generation (all visuals are SVG / Three.js, no diffusion models)
- Multi-layered garments (linings, plackets, cuffs)
- Stretch fabrics with negative ease
- Multiple garment categories (one type only for V1)
- Real-time cloth simulation during cascade
- Mobile UI (desktop browser only)
- User accounts, persistence beyond a session, multi-user
- Production-ready security (it's a hackathon prototype)

---

## Architecture

### Component Map

```
                    ┌─────────────────────────┐
                    │   Browser (User)        │
                    │  - Pattern picker       │
                    │  - Measurement form     │
                    │  - Photo upload         │
                    │  - SVG pattern view     │
                    │  - GSAP cascade anim    │
                    │  - Three.js body view   │
                    └────────────┬────────────┘
                                 │ HTTPS
                    ┌────────────▼────────────┐
                    │   FastAPI Backend       │
                    │  - Routes               │
                    │  - Session management   │
                    │  - Pattern grading      │
                    │  - Cascade orchestration│
                    └─┬─────────┬─────────┬───┘
                      │         │         │
              ┌───────▼──┐  ┌───▼────┐ ┌──▼──────────────┐
              │  SAM 2   │  │ SMPL-X │ │ Managed Agents  │
              │ (segment)│  │  (body)│ │   (Claude)      │
              └──────────┘  └────────┘ └─┬───────────────┘
                                         │
                          ┌──────────────┼──────────────┐
                          │              │              │
                    ┌─────▼────┐   ┌─────▼─────┐  ┌─────▼─────┐
                    │ Shoulder │   │ Bust      │  │ Waist/Hip │
                    │ Agent    │   │ Agent     │  │ Agent     │
                    └─────┬────┘   └─────┬─────┘  └─────┬─────┘
                          └──────────────┼──────────────┘
                                         │
                                  ┌──────▼──────┐
                                  │ Coordinator │
                                  │   Agent     │
                                  └─────────────┘
```

### The Brain/Hands Split

**Claude reasons about:**
- Diagnosing fit issues from muslin photos
- Choosing which adjustments to apply and in what order
- Generating step-by-step narration for cascade animations
- Deciding when the fitting loop has converged (stretch)
- Synthesizing specialist diagnoses into a unified recommendation

**Deterministic code executes:**
- All SVG geometric transforms (slash, spread, rotate, translate)
- Pattern grading math
- SMPL body generation from β parameters
- GSAP animation playback
- SAM 2 segmentation
- File I/O, session state, all infrastructure

**Why this split matters:** Claude is great at "what should happen and why." Code is great at "execute precise geometric operations reproducibly." This division means demos are predictable (geometry is deterministic) while reasoning is rich (Claude explains the why).

### Where Managed Agents Fit

**Use 1: Multi-agent fit diagnosis (V1, headline).** Each specialist agent (shoulder, bust, waist/hip, sleeve, posture) gets the muslin photos + relevant fit theory context, returns a focused diagnosis. Coordinator agent synthesizes. Justifies multi-agent feature as more than gimmick — it mirrors how human experts actually think.

**Use 2: Self-iterating fitting loop (V2, stretch).** Define success criteria (no drag lines, ease within bounds, all seams trued). Managed Agent proposes adjustment → applies → re-evaluates → iterates until convergence or hits a "needs human input" state. Showcases the self-evaluation research-preview feature.

**Use 3: Overnight build delegation (throughout week).** End-of-day spec out well-defined implementation tasks, agent works overnight, wake to working code or clear failures. Effectively expands the build week.

### What the User Sees vs What Happens

| User action | What happens behind the scenes |
|-------------|-------------------------------|
| Selects pattern | Pre-loaded SVG with named elements loads into editor |
| Enters measurements | Map to SMPL β + grade pattern to baseline size, render Three.js body |
| Uploads muslin photos | SAM 2 segments muslin, sends crops + originals to Managed Agent session |
| Clicks "Diagnose" | Specialist agents analyze regions in parallel, coordinator returns issue list |
| Reviews diagnosis | UI shows annotated photo with issues highlighted |
| Clicks "Apply adjustments" | Cascade orchestrator runs FBA / swayback transforms on SVG, GSAP animates each step, Claude narration plays alongside |
| Downloads pattern | SVG/PDF export of adjusted pattern |

---

## Tech Stack

| Layer | Tool | Notes |
|-------|------|-------|
| Reasoning | Claude Opus 4.7 via Managed Agents | Multi-agent + self-iteration features |
| Computer vision | SAM 2 | Segmentation only; reasoning is Claude's job |
| Body model | smplx Python package | SMPL-X, with hardcoded β fallback |
| Pattern rendering | Custom SVG library (built Day 2) | Named, addressable elements |
| Cascade animation | GSAP | Industry standard, Claude knows it well |
| 3D viewer | Three.js | Browser-side, no cloth sim in V1 |
| Backend | FastAPI | Python, fits Steph's existing stack |
| Frontend | Vanilla JS + HTML, or simple React | Whatever ships fastest |
| Deployment | Local for demo; optional Render/Railway | Hackathon doesn't need production deploy |
| Build tooling | Claude Code with managed-agents SDK | For overnight delegation |

---

## Week Plan

Each day has: **Goal**, **Done When** (concrete completion criteria), **Tasks**, **Overnight Agent Spec** (what to delegate while sleeping), **Low-Energy Alternative**.

### Day 1 — Vision capability eval + foundation

**Goal:** Know whether Claude can diagnose muslin photos accurately enough to be the headline feature, and have all foundational infrastructure stood up.

**Done when:**
- Eval results documented: Claude's diagnosis accuracy on 20+ real muslin photos with known correct diagnoses (from forum threads where the answer is given in replies)
- Decision recorded: full vision diagnosis OR fallback to user-driven issue selection
- Hello-world Managed Agent running successfully
- Project repo set up, FastAPI skeleton runs, frontend renders a blank canvas
- SMPL package installed and producing a default body

**Tasks:**
- Scrape 20–30 muslin photos from r/sewing, Cashmerette blog, Curvy Sewing Collective with known diagnoses in the comments
- Test Claude diagnosis accuracy across this set (single-agent, just to baseline)
- Stand up Managed Agents hello-world per Anthropic docs
- Initialize repo with FastAPI + minimal frontend
- Install smplx, verify it works, render one default body

**Overnight Agent Spec:** *"Given the file structure I've set up at [path], implement these endpoint stubs in FastAPI: POST /pattern/load, POST /measurements, POST /diagnose, POST /apply-adjustment. Each should accept the schema in /schemas/, validate inputs, and return placeholder JSON matching the response schema. Add pytest tests that hit each endpoint with valid + invalid inputs. Run tests until all pass."*

**Low-energy alternative:** Skip the eval, commit to fallback (user-driven issue selection from checklist) immediately. Day becomes setup-only.

**Risk note:** This day is the project's biggest unknown. If vision accuracy is below 50%, the entire product framing shifts toward "AI-assisted manual fitting" rather than "AI fit diagnostician." Account for this in the pitch.

---

### Day 2 — Body model, measurements, pattern grading

**Goal:** Pattern + measurements → graded baseline pattern + resized 3D body.

**Done when:**
- User can enter bust/waist/hip/height/back length, see a SMPL body resize accordingly in Three.js
- One garment pattern (fitted t-shirt or bodice) loads as structured SVG with named elements
- Grading function takes the pattern + measurements and returns a graded SVG
- Round trip works: form input → graded pattern displayed in browser

**Tasks:**
- Build measurements → SMPL β: either small regression model on synthetic data, or hardcoded mappings for 5 standard sizes
- Set up Three.js viewer in browser, render SMPL mesh, basic camera controls
- Source/draw the base pattern as SVG with explicit element IDs (front bodice, back bodice, sleeve, dart, etc.)
- Implement grading rules for the chosen garment based on standard size charts (look up Aldrich or Big 4 grading rules)

**Overnight Agent Spec:** *"Build out the SVG pattern manipulation library in /lib/pattern_ops/. It should expose: translate_element(svg, element_id, dx, dy), rotate_element(svg, element_id, angle, pivot), slash_line(svg, from_pt, to_pt), spread_at_line(svg, line_id, distance), add_dart(svg, position, width, length), true_seam_length(svg, seam_a, seam_b). Each function takes an SVG (as parsed object) and returns a new SVG. Write unit tests for each. Reference: I've documented expected behavior in /lib/pattern_ops/SPEC.md."*

**Low-energy alternative:** Skip the regression, hardcode 5 size β vectors. Skip programmatic grading, hand-create graded SVGs for 3 sizes upfront and let user pick.

---

### Day 3 — Photo pipeline + multi-agent diagnosis

**Goal:** Photo in → diagnosed fit issues out, via Managed Agents multi-agent architecture.

**Done when:**
- SAM 2 segments muslin from photo background reliably for staged test images
- Managed Agent session can be invoked from FastAPI
- Multi-agent diagnosis works end-to-end: photos go in, structured diagnosis comes out
- At least 3 specialist agents (shoulder, bust, waist/hip) plus coordinator
- Diagnosis output renders as annotated overlay on the photo

**Tasks:**
- Wire up SAM 2 (Replicate API or local; Replicate easier for hackathon)
- Design specialist agent prompts: each gets photos + region of interest + relevant fit theory snippet, returns JSON diagnosis
- Implement coordinator agent that takes specialist outputs and synthesizes
- Build SVG annotation overlay that draws Claude's identified issues on the original photo
- Connect to FastAPI: POST /diagnose endpoint kicks off agent session, polls or streams results

**Overnight Agent Spec:** *"Refine the specialist agent prompts in /agents/prompts/ to improve diagnosis accuracy on the test set in /tests/diagnosis_fixtures/. Run each prompt against all fixtures, log results, identify failure patterns, propose prompt edits, re-test. Iterate until 70%+ accuracy or 3 iterations completed. Document changes in /agents/prompts/CHANGELOG.md."*

**Low-energy alternative:** Single-agent diagnosis (no specialists), no annotation overlay, just text output of identified issues.

---

### Day 4 — Cascade engine for FBA and swayback

**Goal:** A diagnosed issue → applied adjustment cascade on the pattern, with each step semantically labeled.

**Done when:**
- Apply-FBA function takes pattern SVG + magnitude, returns adjusted SVG via correct sequence of geometric ops
- Apply-swayback function does the same
- Each function emits a structured "cascade script" — JSON list of (action, parameters, narration) tuples — for downstream animation
- End-to-end test: photo → diagnosis → applied cascade → final adjusted pattern

**Tasks:**
- Research FBA cascade rules thoroughly (Curvy Sewing Collective tutorials, Cashmerette blog, Aldrich book if accessible)
- Implement FBA as composed pattern_ops calls; output the cascade script
- Same for swayback
- Have Claude generate the narration for each step (one-time at design, cached — not regenerated per request)
- Connect to FastAPI: POST /apply-adjustment

**Overnight Agent Spec:** *"Build the GSAP animation engine in /frontend/lib/cascade_player/. It should accept a cascade script (schema in /schemas/cascade_script.json) and animate each step on the SVG with smooth transitions, synchronized text narration appearing alongside. Include playback controls (play/pause/restart, step-by-step mode). Test against the example cascade scripts in /tests/cascade_examples/."*

**Low-energy alternative:** FBA only, no swayback. Skip narration generation, use hardcoded text per step.

---

### Day 5 — INTEGRATION DAY (the most important day)

**Goal:** End-to-end flow works from a fresh browser. Demo is technically possible.

**Done when:**
- A user can: load pattern → enter measurements → see body resize → upload muslin photo → see diagnosis → click apply → watch cascade animation → download adjusted pattern
- The flow takes under 90 seconds end-to-end
- Test on a fresh browser session, fresh login if applicable
- Three known-good test scenarios documented and verified working

**Tasks:**
- Wire frontend to all backend endpoints
- Polish the UI flow — clear states, loading indicators, error handling
- Implement the 3 demo scenarios (different bodies, different patterns, different fit issues)
- Test with intentionally broken inputs to ensure graceful failures

**Overnight Agent Spec:** *"Generate a demo dataset: 10 staged muslin photos (using stock body images + overlay technique or synthetic), each paired with a known diagnosis and expected cascade output. Add to /tests/demo_dataset/. Also draft a README.md for the project covering: what it does, who built it, how to run it, architecture summary."*

**Low-energy alternative:** Cut to 2 scenarios. Skip error handling polish.

**Critical note:** STOP ADDING FEATURES at end of Day 5. Days 6–7 are for stretch goals AND polish, with stretch always cuttable.

---

### Day 6 — Stretch features + UI polish

**Goal:** Push the product further, but not at the cost of breaking what works.

**Done when:**
- AT LEAST ONE of: self-iterating fitting loop, additional cascade type, override controls, 3D garment drape — implemented and working
- UI polished to demo-grade
- Demo flow rehearsed at least twice
- List of bugs found in rehearsal, prioritized

**Tasks:**
- Pick ONE stretch feature based on what's most demoable + what's most achievable given remaining time
- UI polish pass: spacing, color, typography, transitions, copy
- Rehearse the demo end-to-end, time it, identify weak moments
- Triage bugs: critical (breaks demo) vs cosmetic (live with it)

**Overnight Agent Spec:** *"Fix the bugs in /demo/bug_list.md, in priority order. For each fix: write a regression test first, then make the change, then verify the regression test passes and no existing tests break. Skip any bug marked 'cosmetic only' — those wait for me. Don't touch /agents/ or /lib/cascade/ — those are stable."*

**Low-energy alternative:** Skip stretch features entirely. Spend the day on polish + rehearsal.

---

### Day 7 — Pitch + demo prep + sleep

**Goal:** Win the demo, not write more code.

**Done when:**
- 2-minute demo video recorded as backup (in case live demo breaks)
- Pitch script written and rehearsed at least 3 times
- Three known-good test scenarios re-verified working
- Submission materials prepared per hackathon requirements
- You've slept

**Tasks:**
- Record screen capture of happy path, with voiceover
- Write pitch script: hook (the muslin moment), problem, demo, technical highlights (what Opus 4.7 does inside), what's next
- DO NOT touch main branch except for hotfix-on-fire situations
- Prepare 3 fallback demo scenarios in priority order
- Rest

**Low-energy alternative:** Skip pitch rehearsal, just record the demo video and call it done.

---

## Risk Pyramid (what to cut first if behind)

**End of Day 3 if behind:**
- Cut multi-agent diagnosis → single-agent
- Cut SAM 2 segmentation → assume clean input
- Cut additional specialist agents

**End of Day 5 if behind:**
- Cut all stretch features
- Cut 3D body view (replace with body diagram)
- Cut PDF export (SVG download is fine)

**Never cut:**
- One working end-to-end happy path
- The cascade animation (it's the demo's emotional moment)
- The pitch story

---

## Open Decisions

1. **Project name** — "The Muslin Whisperer" is a working title. Pick something better before pitch.
2. **Target garment for V1** — fitted t-shirt vs simple bodice block vs A-line skirt. T-shirt is easiest topology; bodice is most demoable for FBA/swayback. Lean bodice.
3. **Whether to include the cascade override / "what if" controls in V1 or push to V2.**
4. **Hosting** — local laptop demo vs deployed. Local is safer; deployed is more professional.
5. **Pattern source** — use a CC-licensed indie pattern, draft one yourself, or use a Big 4 pattern (copyright caution). TBD.

---

## Handoff Notes for Future Claude Sessions

When starting a fresh chat for implementation work, paste the "At a Glance" section + the relevant day's "Goal / Done when / Tasks" section. That's enough context to be useful immediately.

For overnight agent tasks, the "Overnight Agent Spec" sections are written in agent-ready prose — they should work as direct prompts with minor file path adjustments.

The full conversation that produced this plan covers: market positioning rationale, why we pivoted away from Sewformer, the 9-item brainstorm of Claude reasoning use cases, the rationale for the muslin framing, and the discussion of why mixed measurement + photo input is stronger than either alone. Searchable in chat history if context is needed.
