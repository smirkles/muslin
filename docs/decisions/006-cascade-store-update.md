# ADR 006: Cascade Routes Overwrite Session Store After Adjustment

**Status:** Accepted
**Date:** 2026-04-25

## Context

Spec 17 (pattern-download) downloads the SVG stored under a `graded_pattern_id`. Specs 14 (swayback) and 15 (FBA) apply further adjustments on top of a graded pattern. Two storage models were considered:

1. **New id per cascade step** — each cascade call stores a new `GradedPattern` with a fresh UUID; the frontend tracks the latest id.
2. **Overwrite with same id** — cascade routes call `store_graded_pattern` with the same `graded_pattern_id` after modifying the SVG; the download endpoint always gets the latest SVG without the frontend changing the id.

## Decision

Cascade routes (14, 15) **overwrite** the session store entry using the same `graded_pattern_id` after applying their adjustment.

## Rationale

- The download endpoint (spec 17) operates on `graded_pattern_id`. If cascade produced a new id, the frontend would need to capture it and pass it to the download button — adding a new state field to the wizard store.
- Overwriting preserves the same id end-to-end: grade → (optional) swayback → (optional) FBA → download. The wizard store `graded_pattern_id` field set at grading time remains valid for download without update.
- The session store is in-memory and ephemeral; there is no history requirement for V1. Overwriting is safe.

## Consequences

- If a user applies swayback and then downloads, they get the swayback-adjusted SVG. If they then apply FBA, the same id points to the FBA-adjusted SVG. The previous swayback-only version is gone from the store. This is acceptable for V1.
- Cascade route handlers (14, 15) must call `store_graded_pattern(updated)` where `updated.graded_pattern_id` equals the input `graded_pattern_id`. No new UUID is generated.
- This decision is a minor amendment to specs 14 and 15. Both implementations will be updated accordingly when spec 17 is implemented.
