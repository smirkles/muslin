"""Segmenter protocol and shared types — no FastAPI imports."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ConfigError(Exception):
    """Raised when a required configuration value (e.g. API token) is missing."""


@dataclass(frozen=True)
class SegmentationResult:
    """Output of a single segmentation call."""

    photo_id: str
    mask_path: Path
    cropped_path: Path
    confidence: float


class Segmenter(Protocol):
    """Interface for muslin-removal segmentation backends."""

    def segment(
        self,
        photo_path: Path,
        point_prompt: tuple[float, float] | None = None,
    ) -> SegmentationResult: ...
