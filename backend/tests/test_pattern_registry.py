"""Tests for pattern registry lib and GET /patterns routes.

Covers:
- Unit tests for build_registry using tmp_path pytest fixture
- Unit tests for get_pattern — known id returns detail, unknown id raises PatternNotFound
- Integration tests via TestClient — list, load, 404
- SVG validity test: parse response svg with lxml, assert root tag ends with 'svg'
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from lib.pattern_ops import PatternError
from lib.pattern_registry import (
    PatternDetail,
    PatternMeta,
    PatternNotFound,
    build_registry,
    get_pattern,
)
from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Fixtures: temporary patterns directory for unit tests
# ---------------------------------------------------------------------------


def _make_pattern_dir(
    tmp_path: Path, pattern_id: str, name: str, description: str, piece_count: int
) -> Path:
    """Helper to create a minimal valid pattern directory under tmp_path."""
    pattern_dir = tmp_path / pattern_id
    pattern_dir.mkdir()

    svg_filename = f"{pattern_id}.svg"
    meta = {
        "id": pattern_id,
        "name": name,
        "description": description,
        "piece_count": piece_count,
        "svg_file": svg_filename,
    }
    (pattern_dir / "meta.json").write_text(json.dumps(meta))

    svg_content = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">\n'
        '  <g id="front">\n'
        '    <rect x="10" y="10" width="80" height="80"/>\n'
        "  </g>\n"
        "</svg>\n"
    )
    (pattern_dir / svg_filename).write_text(svg_content)

    return pattern_dir


# ---------------------------------------------------------------------------
# Unit tests: build_registry
# ---------------------------------------------------------------------------


class TestBuildRegistry:
    """Unit tests for build_registry using a temporary directory."""

    def test_empty_dir_returns_empty_registry(self, tmp_path: Path) -> None:
        """An empty patterns dir produces an empty registry."""
        registry = build_registry(tmp_path)
        assert registry == {}

    def test_single_pattern_is_registered(self, tmp_path: Path) -> None:
        """A single valid pattern directory is picked up by build_registry."""
        _make_pattern_dir(tmp_path, "test-v1", "Test Pattern", "A test pattern.", 1)
        registry = build_registry(tmp_path)
        assert "test-v1" in registry

    def test_registry_entry_is_pattern_meta(self, tmp_path: Path) -> None:
        """Registry values are PatternMeta instances."""
        _make_pattern_dir(tmp_path, "test-v1", "Test Pattern", "A test pattern.", 1)
        registry = build_registry(tmp_path)
        assert isinstance(registry["test-v1"], PatternMeta)

    def test_meta_fields_populated_correctly(self, tmp_path: Path) -> None:
        """PatternMeta fields match what's in meta.json."""
        _make_pattern_dir(tmp_path, "test-v1", "Test Pattern", "A test pattern.", 3)
        registry = build_registry(tmp_path)
        meta = registry["test-v1"]
        assert meta.id == "test-v1"
        assert meta.name == "Test Pattern"
        assert meta.description == "A test pattern."
        assert meta.piece_count == 3

    def test_svg_path_points_to_existing_file(self, tmp_path: Path) -> None:
        """PatternMeta.svg_path is an existing file."""
        _make_pattern_dir(tmp_path, "test-v1", "Test Pattern", "A test pattern.", 1)
        registry = build_registry(tmp_path)
        assert registry["test-v1"].svg_path.exists()

    def test_multiple_patterns_all_registered(self, tmp_path: Path) -> None:
        """All subdirectories with meta.json are registered."""
        _make_pattern_dir(tmp_path, "alpha-v1", "Alpha", "First.", 2)
        _make_pattern_dir(tmp_path, "beta-v1", "Beta", "Second.", 4)
        registry = build_registry(tmp_path)
        assert "alpha-v1" in registry
        assert "beta-v1" in registry
        assert len(registry) == 2

    def test_non_directory_entries_are_skipped(self, tmp_path: Path) -> None:
        """A plain file in the patterns dir does not cause an error or entry."""
        (tmp_path / "README.md").write_text("notes")
        registry = build_registry(tmp_path)
        assert registry == {}

    def test_dir_without_meta_json_is_skipped(self, tmp_path: Path) -> None:
        """A subdirectory without meta.json is silently skipped."""
        bad_dir = tmp_path / "bad-pattern"
        bad_dir.mkdir()
        registry = build_registry(tmp_path)
        assert registry == {}


# ---------------------------------------------------------------------------
# Unit tests: get_pattern
# ---------------------------------------------------------------------------


class TestGetPattern:
    """Unit tests for get_pattern."""

    def _make_registry(self, tmp_path: Path) -> dict[str, PatternMeta]:
        _make_pattern_dir(tmp_path, "test-v1", "Test Pattern", "A test pattern.", 1)
        return build_registry(tmp_path)

    def test_known_id_returns_pattern_detail(self, tmp_path: Path) -> None:
        """get_pattern returns a PatternDetail for a known id."""
        registry = self._make_registry(tmp_path)
        detail = get_pattern(registry, "test-v1")
        assert isinstance(detail, PatternDetail)

    def test_detail_has_correct_metadata(self, tmp_path: Path) -> None:
        """PatternDetail metadata fields match the registry entry."""
        registry = self._make_registry(tmp_path)
        detail = get_pattern(registry, "test-v1")
        assert detail.id == "test-v1"
        assert detail.name == "Test Pattern"
        assert detail.description == "A test pattern."
        assert detail.piece_count == 1

    def test_detail_svg_is_non_empty_string(self, tmp_path: Path) -> None:
        """PatternDetail.svg is a non-empty string."""
        registry = self._make_registry(tmp_path)
        detail = get_pattern(registry, "test-v1")
        assert isinstance(detail.svg, str)
        assert len(detail.svg) > 0

    def test_detail_svg_contains_svg_element(self, tmp_path: Path) -> None:
        """PatternDetail.svg content contains an <svg> root when parsed."""
        registry = self._make_registry(tmp_path)
        detail = get_pattern(registry, "test-v1")
        root = etree.fromstring(detail.svg.encode())
        assert root.tag.endswith("svg")

    def test_unknown_id_raises_pattern_not_found(self, tmp_path: Path) -> None:
        """get_pattern raises PatternNotFound for an unknown id."""
        registry = self._make_registry(tmp_path)
        with pytest.raises(PatternNotFound):
            get_pattern(registry, "does-not-exist")

    def test_pattern_not_found_is_subclass_of_pattern_error(self) -> None:
        """PatternNotFound is a subclass of PatternError."""
        assert issubclass(PatternNotFound, PatternError)

    def test_pattern_not_found_message_contains_id(self, tmp_path: Path) -> None:
        """PatternNotFound exception message names the unknown id."""
        registry = self._make_registry(tmp_path)
        with pytest.raises(PatternNotFound, match="unknown-id"):
            get_pattern(registry, "unknown-id")


# ---------------------------------------------------------------------------
# Integration tests: GET /patterns
# ---------------------------------------------------------------------------


class TestListPatternsRoute:
    """Integration tests for GET /patterns."""

    def test_returns_200(self) -> None:
        """GET /patterns returns 200 OK."""
        response = client.get("/patterns")
        assert response.status_code == 200

    def test_returns_list(self) -> None:
        """GET /patterns returns a JSON list."""
        response = client.get("/patterns")
        assert isinstance(response.json(), list)

    def test_list_has_at_least_one_entry(self) -> None:
        """GET /patterns returns at least one pattern."""
        response = client.get("/patterns")
        assert len(response.json()) >= 1

    def test_each_entry_has_required_fields(self) -> None:
        """Each entry has id, name, description, piece_count."""
        response = client.get("/patterns")
        for entry in response.json():
            assert "id" in entry
            assert "name" in entry
            assert "description" in entry
            assert "piece_count" in entry

    def test_each_entry_does_not_have_svg_field(self) -> None:
        """List entries do not include the svg field (that's for detail only)."""
        response = client.get("/patterns")
        for entry in response.json():
            assert "svg" not in entry

    def test_bodice_v1_is_in_list(self) -> None:
        """The placeholder pattern bodice-v1 appears in the list."""
        response = client.get("/patterns")
        ids = [entry["id"] for entry in response.json()]
        assert "bodice-v1" in ids


# ---------------------------------------------------------------------------
# Integration tests: GET /patterns/{pattern_id}
# ---------------------------------------------------------------------------


class TestGetPatternRoute:
    """Integration tests for GET /patterns/{pattern_id}."""

    def test_known_id_returns_200(self) -> None:
        """GET /patterns/bodice-v1 returns 200 OK."""
        response = client.get("/patterns/bodice-v1")
        assert response.status_code == 200

    def test_response_has_all_metadata_fields(self) -> None:
        """Response includes id, name, description, piece_count."""
        response = client.get("/patterns/bodice-v1")
        body = response.json()
        assert "id" in body
        assert "name" in body
        assert "description" in body
        assert "piece_count" in body

    def test_response_id_matches_requested(self) -> None:
        """Response id matches the requested pattern_id."""
        response = client.get("/patterns/bodice-v1")
        assert response.json()["id"] == "bodice-v1"

    def test_response_has_svg_field(self) -> None:
        """Response includes an svg field."""
        response = client.get("/patterns/bodice-v1")
        assert "svg" in response.json()

    def test_svg_field_is_non_empty_string(self) -> None:
        """The svg field is a non-empty string."""
        response = client.get("/patterns/bodice-v1")
        svg = response.json()["svg"]
        assert isinstance(svg, str)
        assert len(svg) > 0

    def test_svg_field_parses_as_valid_svg(self) -> None:
        """The svg field parses with lxml and has an <svg> root element."""
        response = client.get("/patterns/bodice-v1")
        svg_text = response.json()["svg"]
        root = etree.fromstring(svg_text.encode())
        # lxml may or may not include namespace: tag is either 'svg' or '{...}svg'
        assert root.tag.endswith("svg")

    def test_unknown_id_returns_404(self) -> None:
        """GET /patterns/nonexistent returns 404."""
        response = client.get("/patterns/nonexistent")
        assert response.status_code == 404

    def test_404_detail_names_unknown_id(self) -> None:
        """404 response detail message names the unknown id."""
        response = client.get("/patterns/nonexistent")
        detail = response.json()["detail"]
        assert "nonexistent" in detail
