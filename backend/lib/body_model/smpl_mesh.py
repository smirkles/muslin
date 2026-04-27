"""SMPL mesh generation — wraps smplx.create + trimesh GLB export.

The SMPL model is loaded once on first call and cached for subsequent requests.
Model loading takes ~2 seconds for a 40 MB pkl file.

The model file check is deferred to first call so the server can start without
SMPL_NEUTRAL.pkl present (e.g. on Railway). Only the body mesh endpoint fails
when the file is missing.
"""

from __future__ import annotations

import io
from pathlib import Path

import trimesh

# ---------------------------------------------------------------------------
# Model path — resolved relative to project root (parent of backend/)
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_MODEL_PATH = _PROJECT_ROOT / "assets" / "smpl_models" / "smpl" / "SMPL_NEUTRAL.pkl"

# ---------------------------------------------------------------------------
# Module-level model cache — populated on first generate_mesh() call
# ---------------------------------------------------------------------------

_smpl_model = None


def _get_model():
    """Return the cached smplx model, loading it on first call."""
    global _smpl_model
    if _smpl_model is None:
        if not _MODEL_PATH.exists():
            raise FileNotFoundError(
                f"SMPL_NEUTRAL.pkl not found at {_MODEL_PATH}. "
                "See docs/setup.md for model download instructions."
            )
        import smplx  # noqa: PLC0415

        _smpl_model = smplx.create(
            str(_MODEL_PATH.parent),
            model_type="smpl",
            gender="neutral",
            num_betas=10,
        )
    return _smpl_model


def generate_mesh(betas: list[float]) -> bytes:
    """Generate a GLB mesh for the given SMPL β vector.

    Args:
        betas: Length-10 SMPL shape parameter vector.

    Returns:
        GLB file bytes (starts with b'glTF').
    """
    import torch  # noqa: PLC0415

    model = _get_model()
    betas_tensor = torch.tensor([betas], dtype=torch.float32)
    output = model(betas=betas_tensor)

    vertices = output.vertices.detach().numpy()[0]  # shape (6890, 3)
    faces = model.faces  # shape (13776, 3)

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    buf = io.BytesIO()
    mesh.export(buf, file_type="glb")
    return buf.getvalue()
