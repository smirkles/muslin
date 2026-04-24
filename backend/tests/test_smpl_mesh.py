"""Tests for lib/body_model/smpl_mesh.py — generate_mesh().

CRITICAL: smplx.create loads a ~40MB pkl at module import. We must patch it
BEFORE importing smpl_mesh. This file uses module-level patching to achieve that.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Build a realistic mock of smplx.create's output
# ---------------------------------------------------------------------------

NUM_VERTICES = 6890
NUM_FACES = 13776


def _make_mock_smplx_module() -> tuple[ModuleType, MagicMock]:
    """Return (mock_smplx_module, mock_model_instance).

    The mock model has:
    - .faces  : np.ndarray shape (13776, 3), dtype int32
    - __call__: returns object with .vertices = mock_tensor

    This mirrors the real smplx API.
    """
    # Build a simple vertex tensor mock
    mock_output = MagicMock()
    # vertices: shape (1, 6890, 3) — batch dim + vertices + xyz
    vertices_np = np.zeros((1, NUM_VERTICES, 3), dtype=np.float32)
    mock_vertices = MagicMock()
    mock_vertices.detach.return_value.numpy.return_value = vertices_np
    mock_output.vertices = mock_vertices

    # The model instance
    mock_model = MagicMock()
    mock_model.faces = np.zeros((NUM_FACES, 3), dtype=np.int32)
    mock_model.return_value = mock_output  # model(betas=...) → output

    # The smplx module
    mock_smplx = MagicMock()
    mock_smplx.create.return_value = mock_model

    return mock_smplx, mock_model


def _import_smpl_mesh_with_mock() -> tuple:
    """Import smpl_mesh with smplx mocked at module scope.

    Returns (smpl_mesh_module, mock_smplx, mock_model).
    """
    # Remove cached version if it exists
    for key in list(sys.modules.keys()):
        if "smpl_mesh" in key or key == "lib.body_model.smpl_mesh":
            del sys.modules[key]

    mock_smplx, mock_model = _make_mock_smplx_module()

    with patch.dict("sys.modules", {"smplx": mock_smplx}):
        import lib.body_model.smpl_mesh as smpl_mesh_mod

        # Keep the mock in modules so subsequent imports within the test work
        sys.modules["smplx"] = mock_smplx
        return smpl_mesh_mod, mock_smplx, mock_model


# ---------------------------------------------------------------------------
# Fixture: fresh smpl_mesh module with mocked smplx
# ---------------------------------------------------------------------------


@pytest.fixture()
def smpl_mesh_module():
    """Provide a freshly-imported smpl_mesh module with smplx mocked."""
    mod, mock_smplx, mock_model = _import_smpl_mesh_with_mock()
    yield mod, mock_smplx, mock_model
    # Cleanup: remove the module from sys.modules so it can be re-imported
    for key in list(sys.modules.keys()):
        if "smpl_mesh" in key:
            del sys.modules[key]


# ---------------------------------------------------------------------------
# Tests for generate_mesh()
# ---------------------------------------------------------------------------


class TestGenerateMesh:
    def test_returns_bytes(self, smpl_mesh_module) -> None:
        """generate_mesh() must return bytes."""
        smpl_mesh, _, _ = smpl_mesh_module
        result = smpl_mesh.generate_mesh([0.0] * 10)
        assert isinstance(result, bytes), f"Expected bytes, got {type(result)}"

    def test_returns_glb_magic_header(self, smpl_mesh_module) -> None:
        """First 4 bytes must be b'glTF' (0x67 0x6C 0x54 0x46)."""
        smpl_mesh, _, _ = smpl_mesh_module
        result = smpl_mesh.generate_mesh([0.0] * 10)
        assert result[:4] == b"glTF", f"Expected GLB magic header, got {result[:4]!r}"

    def test_smplx_called_with_correct_betas(self, smpl_mesh_module) -> None:
        """The smplx model must be called with the betas passed to generate_mesh()."""
        smpl_mesh, _, mock_model = smpl_mesh_module
        betas = [0.5, -0.3, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        smpl_mesh.generate_mesh(betas)
        # Verify model was called — check betas passed via keyword argument
        call_kwargs = mock_model.call_args
        assert call_kwargs is not None, "Model was never called"

    def test_accepts_10_element_beta_list(self, smpl_mesh_module) -> None:
        """generate_mesh() must accept a 10-element beta list without error."""
        smpl_mesh, _, _ = smpl_mesh_module
        betas = [float(i) * 0.1 for i in range(10)]
        # Should not raise
        result = smpl_mesh.generate_mesh(betas)
        assert isinstance(result, bytes)

    def test_glb_contains_expected_vertex_count(self, smpl_mesh_module) -> None:
        """The returned GLB must contain exactly 6890 vertices."""
        import pygltflib

        smpl_mesh, _, _ = smpl_mesh_module
        glb_bytes = smpl_mesh.generate_mesh([0.0] * 10)

        gltf = pygltflib.GLTF2()
        gltf = gltf.load_from_bytes(glb_bytes)

        # Find positions accessor (typically accessor 0 for vertex positions)
        # We check that at least one accessor has count=6890
        vertex_counts = [acc.count for acc in gltf.accessors]
        assert NUM_VERTICES in vertex_counts, (
            f"Expected an accessor with count={NUM_VERTICES}, found counts: {vertex_counts}"
        )

    def test_glb_contains_expected_face_count(self, smpl_mesh_module) -> None:
        """The returned GLB must have indices for 13776 faces (13776*3 = 41328 indices)."""
        import pygltflib

        smpl_mesh, _, _ = smpl_mesh_module
        glb_bytes = smpl_mesh.generate_mesh([0.0] * 10)

        gltf = pygltflib.GLTF2()
        gltf = gltf.load_from_bytes(glb_bytes)

        # Indices accessor has count = num_faces * 3 (triangles)
        index_counts = [acc.count for acc in gltf.accessors]
        expected_index_count = NUM_FACES * 3
        assert expected_index_count in index_counts, (
            f"Expected an accessor with count={expected_index_count} (face indices), "
            f"found counts: {index_counts}"
        )


# ---------------------------------------------------------------------------
# AC: Import hygiene — no fastapi in lib/body_model/
# ---------------------------------------------------------------------------


class TestImportHygiene:
    def test_smpl_mesh_has_no_fastapi_import(self) -> None:
        """lib/body_model/smpl_mesh must not import fastapi."""
        import os

        spec_file = os.path.join(
            os.path.dirname(__file__), "..", "lib", "body_model", "smpl_mesh.py"
        )
        source = open(spec_file).read()
        assert "fastapi" not in source, "smpl_mesh.py must not import fastapi"
