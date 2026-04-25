"""ReplicateSegmenter — calls SAM 2 via the Replicate API."""

import base64
import io
import os
from pathlib import Path

import replicate
from PIL import Image

from lib.segmentation.segmenter import ConfigError, SegmentationResult

_DEFAULT_MODEL = "meta/sam-2"


class ReplicateSegmenter:
    """Segments a garment from a photo using SAM 2 on Replicate."""

    def segment(
        self,
        photo_path: Path,
        point_prompt: tuple[float, float] | None = None,
    ) -> SegmentationResult:
        """Run SAM 2 segmentation on photo_path.

        Raises ConfigError if REPLICATE_API_TOKEN is not set.
        Lets any Replicate SDK exception propagate to the caller.
        """
        token = os.environ.get("REPLICATE_API_TOKEN")
        if not token:
            raise ConfigError("REPLICATE_API_TOKEN is not set in the environment")

        point = point_prompt or (0.5, 0.5)
        model = os.environ.get("REPLICATE_SAM2_MODEL", _DEFAULT_MODEL)

        image_bytes = photo_path.read_bytes()
        b64_image = base64.b64encode(image_bytes).decode()
        # Detect mime type from magic bytes; default to jpeg
        mime = "image/png" if image_bytes[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"

        output = replicate.run(
            model,
            input={
                "image": f"data:{mime};base64,{b64_image}",
                "input_points": [[[point[0], point[1]]]],
                "input_labels": [[1]],
            },
        )

        # Output shape: {"masks": [<readable>], "iou_score": float}
        masks = output.get("masks", [])
        if not masks:
            raise RuntimeError("Replicate returned no masks")

        raw_mask = masks[0]
        mask_bytes = raw_mask.read() if hasattr(raw_mask, "read") else bytes(raw_mask)
        confidence = float(output.get("iou_score", 0.0))

        photo_id = photo_path.stem
        out_dir = photo_path.parent / "segmented"
        out_dir.mkdir(parents=True, exist_ok=True)

        mask_path = out_dir / f"{photo_id}_mask.png"
        mask_path.write_bytes(mask_bytes)

        # Apply mask as alpha channel to produce an RGBA crop
        original = Image.open(photo_path).convert("RGBA")
        mask_img = (
            Image.open(io.BytesIO(mask_bytes)).convert("L").resize(original.size, Image.LANCZOS)
        )
        original.putalpha(mask_img)
        cropped_path = out_dir / f"{photo_id}_cropped.png"
        original.save(cropped_path, "PNG")

        return SegmentationResult(
            photo_id=photo_id,
            mask_path=mask_path,
            cropped_path=cropped_path,
            confidence=confidence,
        )
