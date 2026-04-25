"""Tests for POST /body/mesh endpoint (routes/body.py)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Setup: we must mock smplx BEFORE importing main (which imports routes/body)
# ---------------------------------------------------------------------------

NUM_VERTICES = 6890
NUM_FACES = 13776

# Minimal valid GLB bytes — real GLB starts with 4-byte magic "glTF"
_FAKE_GLB = b"glTF" + b"\x00" * 20


def _make_mock_smplx() -> MagicMock:
    """Build a smplx mock that returns valid-looking mesh data."""
    mock_output = MagicMock()
    vertices_np = np.zeros((1, NUM_VERTICES, 3), dtype=np.float32)
    mock_vertices = MagicMock()
    mock_vertices.detach.return_value.numpy.return_value = vertices_np
    mock_output.vertices = mock_vertices

    mock_model = MagicMock()
    mock_model.faces = np.zeros((NUM_FACES, 3), dtype=np.int32)
    mock_model.return_value = mock_output

    mock_smplx = MagicMock()
    mock_smplx.create.return_value = mock_model
    return mock_smplx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_client():
    """Return a FastAPI TestClient with generate_mesh mocked to return fake GLB.

    We must remove 'main' from sys.modules before each fixture run so that
    from main import app triggers a fresh import under the active patches.
    Without this, a cached main holds stale route bindings that bypass the mock.
    """
    _body_modules = (
        "main",
        "routes.body",
        "lib.body_model.smpl_mesh",
        "lib.body_model.shape_mapping",
    )
    for key in list(sys.modules.keys()):
        if key in _body_modules:
            del sys.modules[key]

    mock_smplx = _make_mock_smplx()

    with patch.dict("sys.modules", {"smplx": mock_smplx}):
        # Patch generate_mesh at the smpl_mesh module level so that routes.body
        # binds the mock when it is freshly imported below.
        with patch("lib.body_model.smpl_mesh.generate_mesh", return_value=_FAKE_GLB):
            from main import app

            yield TestClient(app)

    # Cleanup fresh imports so subsequent fixtures restart cleanly
    for key in list(sys.modules.keys()):
        if key in ("main", "routes.body", "lib.body_model.smpl_mesh"):
            del sys.modules[key]


@pytest.fixture()
def stored_measurement_id(test_client) -> str:
    """POST a measurement and return its UUID for use in body/mesh tests."""
    body = {
        "bust_cm": 92.0,
        "high_bust_cm": 85.0,
        "apex_to_apex_cm": 18.0,
        "waist_cm": 76.0,
        "hip_cm": 100.0,
        "height_cm": 168.0,
        "back_length_cm": 39.5,
    }
    resp = test_client.post("/measurements", json=body)
    assert resp.status_code == 200, f"Setup failed: {resp.json()}"
    return resp.json()["measurement_id"]


# ---------------------------------------------------------------------------
# AC: 200 with valid measurement_id
# ---------------------------------------------------------------------------


class TestBodyMeshEndpointSuccess:
    def test_valid_id_returns_200(self, test_client, stored_measurement_id) -> None:
        """Valid measurement_id → 200 response."""
        resp = test_client.post("/body/mesh", json={"measurement_id": stored_measurement_id})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_valid_id_returns_gltf_content_type(self, test_client, stored_measurement_id) -> None:
        """Valid measurement_id → Content-Type: model/gltf-binary."""
        resp = test_client.post("/body/mesh", json={"measurement_id": stored_measurement_id})
        assert resp.headers["content-type"] == "model/gltf-binary"

    def test_valid_id_body_starts_with_gltf_magic(self, test_client, stored_measurement_id) -> None:
        """Response body starts with b'glTF' magic header."""
        resp = test_client.post("/body/mesh", json={"measurement_id": stored_measurement_id})
        assert resp.content[:4] == b"glTF", f"Expected GLB magic, got {resp.content[:4]!r}"


# ---------------------------------------------------------------------------
# AC: 404 for unknown measurement_id
# ---------------------------------------------------------------------------


class TestBodyMeshEndpointNotFound:
    def test_unknown_id_returns_404(self, test_client) -> None:
        """Unknown measurement_id → 404."""
        resp = test_client.post(
            "/body/mesh", json={"measurement_id": "00000000-0000-0000-0000-000000000000"}
        )
        assert resp.status_code == 404

    def test_unknown_id_returns_correct_detail(self, test_client) -> None:
        """Unknown measurement_id → {"detail": "measurement not found"}."""
        resp = test_client.post(
            "/body/mesh", json={"measurement_id": "00000000-0000-0000-0000-000000000000"}
        )
        assert resp.json()["detail"] == "measurement not found"


# ---------------------------------------------------------------------------
# AC: 500 when smplx raises
# ---------------------------------------------------------------------------


class TestBodyMeshEndpointSmplxFailure:
    def test_smplx_error_returns_500(self, stored_measurement_id) -> None:
        """When generate_mesh raises, endpoint returns 500."""
        # Patch the name in routes.body's namespace (where the route looks it up).
        # Patching lib.body_model.smpl_mesh.generate_mesh would not work because
        # routes.body already holds its own local binding to the function.
        import main

        with patch("routes.body.generate_mesh", side_effect=RuntimeError("smplx crashed")):
            client = TestClient(main.app, raise_server_exceptions=False)
            resp = client.post("/body/mesh", json={"measurement_id": stored_measurement_id})
            assert resp.status_code == 500

    def test_smplx_error_returns_correct_detail(self, stored_measurement_id) -> None:
        """When generate_mesh raises, detail is "mesh generation failed"."""
        import main

        with patch("routes.body.generate_mesh", side_effect=RuntimeError("smplx crashed")):
            client = TestClient(main.app, raise_server_exceptions=False)
            resp = client.post("/body/mesh", json={"measurement_id": stored_measurement_id})
            assert resp.json()["detail"] == "mesh generation failed"


# ---------------------------------------------------------------------------
# AC: SMPL betas match measurements_to_betas()
# ---------------------------------------------------------------------------


class TestBodyMeshUsesCorrectBetas:
    def test_generate_mesh_called_with_correct_betas(
        self, test_client, stored_measurement_id
    ) -> None:
        """POST /body/mesh calls generate_mesh with betas from measurements_to_betas()."""
        from lib.body_model.shape_mapping import measurements_to_betas
        from lib.measurements import get_measurements

        stored = get_measurements(stored_measurement_id)
        expected_betas = measurements_to_betas(stored)

        with patch("routes.body.generate_mesh", return_value=_FAKE_GLB) as mock_gen:
            test_client.post("/body/mesh", json={"measurement_id": stored_measurement_id})
            mock_gen.assert_called_once_with(expected_betas)
