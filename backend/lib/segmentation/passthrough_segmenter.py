"""PassthroughSegmenter — skips SAM 2, copies the original photo as the crop.

Used when REPLICATE_API_TOKEN is not configured. The diagnosis endpoint
receives the original photo bytes, which Claude can analyse just as well
without a masked crop for the purposes of fit diagnosis.
"""

import shutil
from pathlib import Path

from lib.segmentation.segmenter import SegmentationResult


class PassthroughSegmenter:
    """Segmenter that passes the original photo through without masking."""

    def segment(
        self,
        photo_path: Path,
        point_prompt: tuple[float, float] | None = None,
    ) -> SegmentationResult:
        photo_id = photo_path.stem
        out_dir = photo_path.parent / "segmented"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Write a blank 1x1 mask so callers that expect a mask file don't break
        mask_path = out_dir / f"{photo_id}_mask.png"
        if not mask_path.exists():
            _write_blank_mask(mask_path)

        # Copy the original as the crop — no masking applied
        cropped_path = out_dir / f"{photo_id}_cropped.png"
        shutil.copy2(photo_path, cropped_path)

        return SegmentationResult(
            photo_id=photo_id,
            mask_path=mask_path,
            cropped_path=cropped_path,
            confidence=1.0,
        )


def _write_blank_mask(path: Path) -> None:
    """Write a minimal 1×1 white PNG to path."""
    # Minimal valid 1×1 white PNG (no Pillow dependency)
    import base64

    blank_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )
    path.write_bytes(blank_png)
