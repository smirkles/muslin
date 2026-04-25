"""Route tests for GET /patterns/download/{graded_pattern_id} — spec 17-pattern-download.

Covers AC:
- ?format=svg → 200, Content-Type: image/svg+xml, correct Content-Disposition
- ?format=pdf → 200, Content-Type: application/pdf, body starts with %PDF-
- no format param → SVG (default)
- unknown graded_pattern_id → 404 with detail mentioning the id
- format=xyz → 422
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from lib.grading import GradedPattern, store_graded_pattern
from main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 300">
  <g id="bodice-front"><rect x="10" y="10" width="100" height="200"/></g>
</svg>"""


def _store_graded() -> str:
    """Store a sample GradedPattern and return its graded_pattern_id."""
    gid = str(uuid.uuid4())
    graded = GradedPattern(
        graded_pattern_id=gid,
        pattern_id="bodice-v1",
        measurement_id="test-m-route-001",
        svg=SAMPLE_SVG,
        adjustments_cm={"bust": 2.0, "waist": 1.0, "hip": 3.0, "back_length": 0.5},
    )
    store_graded_pattern(graded)
    return gid


# ---------------------------------------------------------------------------
# SVG download
# ---------------------------------------------------------------------------


class TestSvgDownloadRoute:
    def test_svg_format_returns_200(self) -> None:
        gid = _store_graded()
        resp = client.get(f"/patterns/download/{gid}?format=svg")
        assert resp.status_code == 200, resp.text

    def test_svg_content_type(self) -> None:
        gid = _store_graded()
        resp = client.get(f"/patterns/download/{gid}?format=svg")
        assert resp.headers["content-type"] == "image/svg+xml"

    def test_svg_content_disposition(self) -> None:
        gid = _store_graded()
        resp = client.get(f"/patterns/download/{gid}?format=svg")
        assert "attachment" in resp.headers["content-disposition"]
        assert "muslin-pattern.svg" in resp.headers["content-disposition"]

    def test_default_format_is_svg(self) -> None:
        gid = _store_graded()
        resp = client.get(f"/patterns/download/{gid}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/svg+xml"


# ---------------------------------------------------------------------------
# PDF download
# ---------------------------------------------------------------------------


class TestPdfDownloadRoute:
    def test_pdf_format_returns_200(self) -> None:
        gid = _store_graded()
        resp = client.get(f"/patterns/download/{gid}?format=pdf")
        assert resp.status_code == 200, resp.text

    def test_pdf_content_type(self) -> None:
        gid = _store_graded()
        resp = client.get(f"/patterns/download/{gid}?format=pdf")
        assert resp.headers["content-type"] == "application/pdf"

    def test_pdf_body_starts_with_pdf_header(self) -> None:
        gid = _store_graded()
        resp = client.get(f"/patterns/download/{gid}?format=pdf")
        assert resp.content[:5] == b"%PDF-"

    def test_pdf_content_disposition(self) -> None:
        gid = _store_graded()
        resp = client.get(f"/patterns/download/{gid}?format=pdf")
        assert "attachment" in resp.headers["content-disposition"]
        assert "muslin-pattern.pdf" in resp.headers["content-disposition"]


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestDownloadRouteErrors:
    def test_unknown_id_returns_404(self) -> None:
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/patterns/download/{fake_id}?format=svg")
        assert resp.status_code == 404

    def test_unknown_id_detail_mentions_id(self) -> None:
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/patterns/download/{fake_id}?format=svg")
        assert fake_id in resp.json()["detail"]

    def test_invalid_format_returns_422(self) -> None:
        gid = _store_graded()
        resp = client.get(f"/patterns/download/{gid}?format=xyz")
        assert resp.status_code == 422

    def test_invalid_format_detail_mentions_format(self) -> None:
        gid = _store_graded()
        resp = client.get(f"/patterns/download/{gid}?format=xyz")
        detail = resp.json()["detail"]
        # Either a string or list from FastAPI validation
        detail_str = str(detail)
        assert (
            "format" in detail_str.lower()
            or "svg" in detail_str.lower()
            or "pdf" in detail_str.lower()
        )
