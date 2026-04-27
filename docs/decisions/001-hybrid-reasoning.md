# ADR 001: Hybrid Reasoning + Deterministic Geometry

**Status:** Accepted
**Date:** 2026-04-23

## Context

Iris Tailor's core capability is applying pattern adjustments (FBA, swayback, grading) based on AI-diagnosed fit issues. Two architectural options existed:

1. **Pure AI:** Claude predicts the entire adjusted pattern as output (e.g. Sewformer-style mesh generation).
2. **Pure deterministic:** Hardcoded rules for every adjustment type; AI only classifies fit issues from photos.
3. **Hybrid:** AI diagnoses issues and orchestrates which adjustments to apply; deterministic code executes the geometric transforms.

## Decision

We chose the **hybrid** approach.

- **Claude reasons:** diagnoses fit issues from muslin photos, chooses adjustments, orchestrates cascade sequence, narrates each step.
- **Deterministic code executes:** all SVG geometric operations (translate, rotate, slash, spread, add dart, true seam) through the `backend/lib/pattern_ops/` library.

## Consequences

### Positive

- **Reproducibility.** Given the same diagnosis + magnitudes, the geometric output is identical every run. Critical for a live demo.
- **Learnability.** The cascade's steps are named, ordered, and can be animated with clear narration. An AI-generated mesh cannot be explained step-by-step.
- **Debuggability.** Failures in geometric operations produce specific, fixable errors rather than "the model got it wrong."
- **Testability.** The geometric library has 90%+ unit test coverage. AI reasoning is evaluated separately via the prompt eval harness.
- **Manufacturability.** The output is a real sewing pattern with seams and darts, not an approximation.

### Negative

- **Limited to codified adjustments.** If Steph wants to support a new adjustment type, someone has to implement the geometric rules. Pure-AI approaches could theoretically generalize.
- **More code to maintain.** The pattern_ops library and cascade logic are non-trivial.
- **AI is bottlenecked by the adjustments we support.** If Claude diagnoses an issue we can't execute, we have to either refuse or approximate.

### Mitigation

- V1 intentionally supports only FBA and swayback — the two most common adjustments. The architecture supports adding more cascades as separate specs.
- The diagnosis output includes confidence and free-text reasoning, so even when we can't execute, we can surface the diagnosis to the user.

## Alternatives considered

- **Sewformer / GarmentDiffusion style neural pattern generation:** rejected because generated patterns lack seam correctness and manufacturability; also much harder to fine-tune in hackathon timeline.
- **Pure deterministic with manual issue selection:** rejected because it loses the magic of automated diagnosis from photos, which is the headline demo moment.

## References

- `docs/v2-plan.md` — project plan
- Sewformer paper (rejected approach): https://arxiv.org/abs/2311.04218
