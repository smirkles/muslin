# Spec: Pattern Download (SVG + PDF)

**Spec ID:** 17-pattern-download
**Status:** ready-for-implementation
**Created:** 2026-04-25
**Depends on:** 10-pattern-grading, 14-swayback-cascade, 15-fba-cascade, 08-frontend-plumbing

## What it does

Lets a user download their adjusted pattern — either the size-graded baseline or the cascade-adjusted result — as a single SVG file or a print-ready PDF. Home sewers print the PDF on A4 at true physical scale, tape the tiled pages together, and cut fabric from it. This is the point where the app produces something the user can actually sew with. SVG download is a V1 must-have; PDF is the nice-to-have tier of this spec.

## User-facing behavior

On the results page after grading and (optionally) a cascade, a "Download" button appears with a two-state toggle: **SVG** and **PDF**. Clicking "Download" triggers a browser download of `muslin-pattern.svg` or `muslin-pattern.pdf`. While the PDF is rendering, the button shows a loading state. On error, an inline message appears. The button is disabled until a `graded_pattern_id` is present in the wizard store.

The PDF header reads: **Muslin — Adjusted Pattern**, followed by the current date, the `pattern_id`, and a one-line measurement summary (e.g. `Bust 96 cm · Waist 78 cm · Hip 104 cm · Back length 41 cm`). A footer on every page reads: `Seam allowance: 1.5 cm — already included · Page N of M`.

## Inputs and outputs

### Endpoints

```
GET /patterns/download/{graded_pattern_id}?format=svg
GET /patterns/download/{graded_pattern_id}?format=pdf
```

`format` defaults to `svg` if omitted.

### Responses

**SVG (200):**
- `Content-Type: image/svg+xml`
- `Content-Disposition: attachment; filename="muslin-pattern.svg"`

**PDF (200):**
- `Content-Type: application/pdf`
- `Content-Disposition: attachment; filename="muslin-pattern.pdf"`
- One pattern piece per A4 page at 1:1 physical scale.

### Errors

- **404** — `graded_pattern_id` not in session store → `{"detail": "Pattern '<id>' not found"}`.
- **422** — `format` not `svg` or `pdf` → `{"detail": "format must be 'svg' or 'pdf'"}`.
- **500** — PDF rendering fails → `{"detail": "Failed to render PDF: <reason>"}`.

### Library interface — `backend/lib/export/`

```python
# svg_export.py
def build_svg_download(graded: GradedPattern) -> tuple[str, str]:
    """Return (svg_string, filename)."""

# pdf_export.py
def build_pdf_download(
    graded: GradedPattern,
    measurements: MeasurementsResponse,
    today: date,
) -> tuple[bytes, str]:
    """Return (pdf_bytes, filename)."""
```

## Acceptance criteria

### Library — SVG

- [ ] Given a `GradedPattern` with a valid SVG, `build_svg_download` returns that exact string as the first element and `"muslin-pattern.svg"` as the second.
- [ ] `backend/lib/export/` contains no `fastapi` imports (import-hygiene test).

### Library — PDF

- [ ] `build_pdf_download` returns bytes starting with `%PDF-`.
- [ ] Given a pattern with 4 top-level `<g>` piece elements, the PDF has 4 pages.
- [ ] Every page is A4 portrait — 595 x 842 PDF points (±1 pt).
- [ ] Every page contains `"Muslin — Adjusted Pattern"` in its header (via `pypdf` text extraction).
- [ ] Every page header contains the ISO date string for the `today` argument.
- [ ] Every page header contains the four measurement values formatted in cm.
- [ ] Every page footer contains `"Seam allowance: 1.5 cm"` and `"Page <n> of <m>"`.
- [ ] Physical scale: 1 cm in SVG (5 px) renders as 1 cm on the PDF page (~28.35 pt), within ±2 pt.
- [ ] Pieces rendered in sorted id order for deterministic page order.
- [ ] If a piece exceeds printable A4 area, the PDF still renders with a `"Piece too large for A4"` footnote on that page.
- [ ] `build_pdf_download` does not mutate the input `GradedPattern`.

### Route

- [ ] `GET /patterns/download/{id}?format=svg` returns 200 with correct `Content-Type` and `Content-Disposition`.
- [ ] `GET /patterns/download/{id}?format=pdf` returns 200 with `Content-Type: application/pdf` and body starting with `%PDF-`.
- [ ] `GET /patterns/download/{id}` without `format` returns SVG.
- [ ] Unknown `graded_pattern_id` returns 404 with detail mentioning the id.
- [ ] `format=xyz` returns 422.

### Frontend

- [ ] `DownloadButton` component is disabled when `wizard.graded_pattern_id` is null.
- [ ] Clicking "Download" calls `downloadPattern(graded_pattern_id, format)` which fetches the blob and triggers a browser download.
- [ ] While PDF request is in flight, button shows a spinner and is disabled.
- [ ] On fetch error, an inline error message appears below the button.
- [ ] Vitest test: clicking PDF + Download triggers `fetch` with URL `/patterns/download/{id}?format=pdf`.
- [ ] `pnpm test` passes; `pnpm lint` exits 0.
- [ ] `uv run pytest` passes; `uv run ruff check . && uv run black --check .` exit 0.

## Out of scope

- Tiling large pattern pieces across multiple A4 pages.
- Letter size, A3, A0, or plotter output.
- Seam-allowance toggling (1.5 cm baked in).
- Cutting layout / marker making.
- Emailing or cloud-storing the download.
- Downloading from `pattern_id` alone — must go through `graded_pattern_id`.

## Technical approach

- **PDF library: `svglib` + `reportlab`** — pure Python, no system-level deps. Flag as ADR before coding.
- `backend/lib/export/svg_export.py` — trivial wrapper.
- `backend/lib/export/pdf_export.py` — split SVG into top-level `<g>` pieces, render each via `svglib.svg2rlg` onto a fresh A4 `reportlab` canvas page. Scale: `PX_PER_CM = 5` (import from `backend/lib/cascade/constants.py`).
- `backend/routes/patterns.py` — new `GET /patterns/download/{id}` endpoint. Thin: look up `GradedPattern`, dispatch to export lib, return `Response`/`StreamingResponse`.
- **Storage model:** cascade routes (14, 15) call `store_graded_pattern` with the same id after adjusting, so the session store always holds the latest SVG. Small amendment to those specs — see open questions.
- `frontend/src/components/DownloadButton.tsx` — toggle + fetch + `window.URL.createObjectURL` download trigger.
- `frontend/src/lib/api.ts` — add `downloadPattern(id, format) -> Promise<{blob, filename}>`.

## Dependencies

- External libraries: `svglib`, `reportlab` (add via `uv add`), `pypdf` (dev/test only: `uv add --group dev pypdf`).
- Specs first: 10 (grading + session store), 14 + 15 (cascade overwrites stored SVG), 08 (wizard store).
- Requires two ADRs before coding (see open questions).

## Testing approach

- **Unit tests** in `backend/tests/test_export_svg.py` and `backend/tests/test_export_pdf.py`.
- **Route tests** in `backend/tests/test_routes_patterns_download.py`.
- **Import-hygiene test**: `backend/lib/export/` has no `fastapi` imports.
- **Frontend tests** in `frontend/src/components/__tests__/DownloadButton.test.tsx`.
- **Manual verification**: grade bodice-v1, apply swayback, download PDF, print A4 at 100%, measure a known dimension with a ruler.

## Open questions

1. **Storage model after cascade** — recommended: amend specs 14 and 15 so cascade routes call `store_graded_pattern(updated)` with the same `graded_pattern_id` after adjusting. File as ADR before coding.
2. **PDF library** — recommended: `svglib` + `reportlab` (no system deps). Alternative: `weasyprint` (better SVG fidelity but requires cairo/pango). File as ADR before coding.
3. **Tiling** — V1 explicitly excludes it. If a bodice-v1 piece exceeds A4 at realistic measurements, fall back to SVG-only download for the demo.

## Notes for implementer

- `backend/lib/export/` must not import from `fastapi`, `starlette`, or `routes/`.
- Physical scale constant `PX_PER_CM = 5` — import from `backend/lib/cascade/constants.py`, do not redefine.
- A4 in points: 595.27 × 841.89. Use `reportlab.lib.pagesizes.A4`. Margins: 15 mm = 42.52 pt.
- Per-piece splitting: wrap each `<g>` in a fresh minimal SVG root with the piece's bounding box viewBox so `svglib` can render it standalone.
- `svglib` requires `xmlns="http://www.w3.org/2000/svg"` on the root element — pattern_ops already includes it.
- Write failing tests first per `CLAUDE.md` rule 5.
- File both ADRs before writing any code.
