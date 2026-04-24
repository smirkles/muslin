"""Pattern registry — in-memory catalogue of available sewing patterns.

Patterns are loaded at module import time from the ``patterns/`` directory
adjacent to this file.  Each pattern lives in its own subdirectory containing
a ``meta.json`` file and an SVG file named in that JSON.

Public API
----------
build_registry(patterns_dir) -> dict[str, PatternMeta]
    Scan a directory and return a registry mapping pattern id → PatternMeta.
    Used directly by tests (via tmp_path) and indirectly via the module singleton.

get_pattern(registry, pattern_id) -> PatternDetail
    Return full detail (metadata + SVG content) for a known id.
    Raises PatternNotFound for unknown ids.

REGISTRY
    Module-level singleton built from the real patterns directory at import time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from lib.pattern_ops import PatternError

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PatternNotFound(PatternError):
    """Raised when a requested pattern id is not in the registry."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PatternMeta:
    """Metadata for a pattern (no SVG content — used for list responses)."""

    id: str
    name: str
    description: str
    piece_count: int
    svg_path: Path  # resolved absolute path; not included in API responses


@dataclass
class PatternDetail(PatternMeta):
    """Full pattern detail including SVG content (used for single-pattern responses)."""

    svg: str  # raw SVG file contents as a string


# ---------------------------------------------------------------------------
# Registry builder
# ---------------------------------------------------------------------------


def build_registry(patterns_dir: Path) -> dict[str, PatternMeta]:
    """Scan ``patterns_dir`` and return a mapping of pattern id → PatternMeta.

    Each immediate subdirectory that contains a ``meta.json`` file is treated
    as a pattern entry.  Entries without ``meta.json`` are silently skipped.
    Plain files at the top level are also skipped without error.
    """
    registry: dict[str, PatternMeta] = {}

    for entry in patterns_dir.iterdir():
        if not entry.is_dir():
            continue

        meta_path = entry / "meta.json"
        if not meta_path.exists():
            continue

        raw = json.loads(meta_path.read_text(encoding="utf-8"))
        svg_path = entry / raw["svg_file"]

        meta = PatternMeta(
            id=raw["id"],
            name=raw["name"],
            description=raw["description"],
            piece_count=raw["piece_count"],
            svg_path=svg_path,
        )
        registry[meta.id] = meta

    return registry


# ---------------------------------------------------------------------------
# Pattern detail retrieval
# ---------------------------------------------------------------------------


def get_pattern(registry: dict[str, PatternMeta], pattern_id: str) -> PatternDetail:
    """Return full detail for ``pattern_id``, loading SVG from disk.

    Raises PatternNotFound if ``pattern_id`` is not in ``registry``.
    """
    meta = registry.get(pattern_id)
    if meta is None:
        raise PatternNotFound(f"Pattern '{pattern_id}' not found")

    svg_content = meta.svg_path.read_text(encoding="utf-8")

    return PatternDetail(
        id=meta.id,
        name=meta.name,
        description=meta.description,
        piece_count=meta.piece_count,
        svg_path=meta.svg_path,
        svg=svg_content,
    )


# ---------------------------------------------------------------------------
# Module-level singleton (built at import time)
# ---------------------------------------------------------------------------

_PATTERNS_DIR = Path(__file__).parent / "patterns"
REGISTRY: dict[str, PatternMeta] = build_registry(_PATTERNS_DIR)
