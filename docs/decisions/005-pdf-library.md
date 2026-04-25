# ADR 005: PDF Rendering Library for Pattern Download

**Status:** Accepted
**Date:** 2026-04-25

## Context

Spec 17 (pattern-download) requires rendering a graded SVG pattern as a print-ready PDF with one piece per A4 page at 1:1 physical scale. Three library stacks were evaluated:

1. **svglib + reportlab** — spec's original recommendation. Investigation revealed svglib 1.6.0 hard-requires `rlpycairo`, which requires `pycairo`, which requires the Cairo C library. This is a system-level dependency that fails to build in a standard venv on macOS without Homebrew Cairo. The spec's "no system deps" claim is incorrect for svglib ≥ 1.6.
2. **weasyprint** — higher SVG fidelity (CSS-aware), but explicitly requires Cairo and Pango system libraries.
3. **fpdf2** — pure Python; dependencies are `defusedxml`, `Pillow`, and `fonttools`, all of which are pure Python or have pre-built wheels. Has a built-in SVG parser that handles standard SVG path commands (M/L/C/Q/A/Z), transforms, and basic shapes. Smoke-tested successfully against bodice-v1.svg.

## Decision

Use **fpdf2**.

## Rationale

- Genuinely no system dependencies — works in a standard `uv`-managed venv on any macOS/Linux without Homebrew or pkg-config.
- fpdf2's SVG support handles the full set of path commands and transforms used in sewing-pattern SVGs (verified by smoke test with bodice-v1.svg → 1340-byte valid PDF).
- fpdf2 provides direct control over page size (A4), margins, headers, footers, and unit systems (mm or pt), making it straightforward to implement per-piece A4 pages with measurement summaries.
- Physical scaling: fpdf2 uses mm units; `PX_PER_CM = 5.0` → 1 SVG px = 0.2 cm → 2 mm in PDF coordinates. Exact 1:1 physical scale is achievable.
- `pypdf` (test-only dep) can extract text from the generated PDF to assert header/footer content.

## Consequences

- fpdf2's SVG parser covers standard SVG primitives but may not handle CSS custom properties, `<use>` with external hrefs, or complex filters. Pattern SVGs in this project avoid those features.
- If SVG complexity increases in a future spec (filters, CSS variables, complex text), revisit and consider weasyprint with a Docker base image, accepting the system-dep cost.
- The `reportlab` package was added to `pyproject.toml` but is no longer needed by this feature. It may remain if other specs use it, but it is not a dependency of `lib/export/`.
