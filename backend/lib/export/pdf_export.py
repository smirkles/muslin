"""PDF download export for graded patterns.

No FastAPI imports — this module is pure logic.

One pattern piece per A4 page at 1:1 physical scale (PX_PER_CM = 5).
Header: title, date, pattern_id, piece_id, measurement summary.
Footer: seam-allowance note + page N of M.
"""

from __future__ import annotations

import copy
import os
import tempfile
from datetime import date
from typing import Protocol

from fpdf import FPDF
from lxml import etree

from lib.cascade.constants import PX_PER_CM
from lib.grading import GradedPattern
from lib.pattern_ops import element_bbox

# ---------------------------------------------------------------------------
# Physical scale constants
# ---------------------------------------------------------------------------

MM_PER_PX: float = 10.0 / PX_PER_CM  # 2.0 mm per SVG px (PX_PER_CM = 5)
A4_W_MM: float = 210.0
A4_H_MM: float = 297.0
MARGIN_MM: float = 15.0
FOOTER_RESERVE_MM: float = 12.0  # space from bottom edge for footer
PRINTABLE_W_MM: float = A4_W_MM - 2 * MARGIN_MM
PRINTABLE_H_MM: float = A4_H_MM - 2 * MARGIN_MM


# ---------------------------------------------------------------------------
# Measurements protocol (compatible with lib.measurements.MeasurementsResponse)
# ---------------------------------------------------------------------------


class _MeasurementsLike(Protocol):
    bust_cm: float
    waist_cm: float
    hip_cm: float
    back_length_cm: float


# ---------------------------------------------------------------------------
# Internal: piece SVG helper
# ---------------------------------------------------------------------------


_SVG_NS = "http://www.w3.org/2000/svg"


def _piece_svg_string(piece_el: etree._Element) -> str:
    """Return a minimal SVG string wrapping a single piece <g> element."""
    bbox = element_bbox(piece_el)
    if bbox is not None:
        min_x, min_y, max_x, max_y = bbox
        vb = f"{min_x} {min_y} {max_x - min_x} {max_y - min_y}"
        w_attr = str(max_x - min_x)
        h_attr = str(max_y - min_y)
    else:
        vb = "0 0 100 100"
        w_attr = "100"
        h_attr = "100"

    new_root = etree.Element(f"{{{_SVG_NS}}}svg")
    new_root.set("xmlns", _SVG_NS)
    new_root.set("viewBox", vb)
    new_root.set("width", w_attr)
    new_root.set("height", h_attr)
    new_root.append(copy.deepcopy(piece_el))
    return etree.tostring(new_root, encoding="unicode")


def _is_oversized(piece_el: etree._Element, avail_w_mm: float, avail_h_mm: float) -> bool:
    bbox = element_bbox(piece_el)
    if bbox is None:
        return False
    min_x, min_y, max_x, max_y = bbox
    w_mm = (max_x - min_x) * MM_PER_PX
    h_mm = (max_y - min_y) * MM_PER_PX
    return w_mm > avail_w_mm or h_mm > avail_h_mm


# ---------------------------------------------------------------------------
# PDF class with header/footer
# ---------------------------------------------------------------------------


class _PatternPDF(FPDF):
    def __init__(
        self,
        graded: GradedPattern,
        measurements: _MeasurementsLike,
        today: date,
        total_pages: int,
    ) -> None:
        super().__init__(format="A4", unit="mm")
        self._graded = graded
        self._measurements = measurements
        self._today = today
        self._total_pages = total_pages
        self.current_piece_id: str = ""
        self.is_oversized: bool = False

    def header(self) -> None:
        meas = self._measurements
        meas_line = (
            f"Bust {meas.bust_cm:.0f} cm  "
            f"Waist {meas.waist_cm:.0f} cm  "
            f"Hip {meas.hip_cm:.0f} cm  "
            f"Back length {meas.back_length_cm:.0f} cm"
        )
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, "Iris Tailor - Adjusted Pattern", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        piece_line = (
            f"{self._today.isoformat()} · {self._graded.pattern_id} · {self.current_piece_id}"
        )
        if self.is_oversized:
            piece_line += " · Piece too large for A4"
        self.cell(0, 5, piece_line, new_x="LMARGIN", new_y="NEXT")
        self.cell(0, 5, meas_line, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-FOOTER_RESERVE_MM)
        self.set_font("Helvetica", "", 8)
        self.cell(
            0,
            10,
            f"Seam allowance: 1.5 cm - already included   Page {self.page_no()} of {{nb}}",
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_pdf_download(
    graded: GradedPattern,
    measurements: _MeasurementsLike,
    today: date,
) -> tuple[bytes, str]:
    """Return (pdf_bytes, filename) for a graded pattern PDF download.

    One A4 page per pattern piece, in sorted piece-id order.
    """
    root = etree.fromstring(graded.svg.encode())
    ns_map = {"svg": _SVG_NS}
    piece_els = {g.get("id"): g for g in root.findall("svg:g[@id]", ns_map)}
    sorted_ids = sorted(piece_els.keys())

    pdf = _PatternPDF(graded, measurements, today, len(sorted_ids))
    pdf.alias_nb_pages()
    pdf.set_margins(left=MARGIN_MM, top=MARGIN_MM, right=MARGIN_MM)
    pdf.set_auto_page_break(auto=True, margin=FOOTER_RESERVE_MM)

    for piece_id in sorted_ids:
        piece_el = piece_els[piece_id]
        # is_oversized must be set before add_page() so header() can include the note
        pdf.current_piece_id = piece_id
        pdf.is_oversized = _is_oversized(
            piece_el, PRINTABLE_W_MM, PRINTABLE_H_MM - FOOTER_RESERVE_MM
        )
        pdf.add_page()

        body_top = pdf.get_y()
        avail_w = PRINTABLE_W_MM
        avail_h = A4_H_MM - body_top - MARGIN_MM - FOOTER_RESERVE_MM

        piece_svg = _piece_svg_string(piece_el)
        bbox = element_bbox(piece_el)

        if bbox is not None:
            min_x, min_y, max_x, max_y = bbox
            pw_mm = (max_x - min_x) * MM_PER_PX
            ph_mm = (max_y - min_y) * MM_PER_PX
            scale = min(avail_w / pw_mm, avail_h / ph_mm, 1.0)
            render_w = pw_mm * scale
        else:
            render_w = avail_w

        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w") as tmp:
            tmp.write(piece_svg)
            tmp_path = tmp.name
        try:
            pdf.image(tmp_path, x=MARGIN_MM, y=body_top, w=render_w)
        finally:
            os.unlink(tmp_path)

    return bytes(pdf.output()), "iris-tailor-pattern.pdf"
