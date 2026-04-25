"""Route tests for POST /diagnosis/run.

All tests use get_agent patched to avoid real Anthropic calls.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_response(text: str) -> MagicMock:
    """Build a mock AgentResponse."""
    from lib.diagnosis.agent import AgentResponse

    return AgentResponse(text=text, model="claude-opus-4-7", input_tokens=10, output_tokens=20)


def _make_specialist_json(region: str, issue_type: str = "test_issue") -> str:
    return json.dumps(
        {
            "region": region,
            "issues": [
                {
                    "issue_type": issue_type,
                    "confidence": 0.8,
                    "description": f"Test issue for {region}",
                    "recommended_adjustment": "Test adjustment",
                }
            ],
        }
    )


def _make_coordinator_json(cascade_type: str = "fba") -> str:
    return json.dumps(
        {
            "issues": [
                {
                    "issue_type": "pulling_across_bust",
                    "confidence": 0.85,
                    "description": "Main issue found",
                    "recommended_adjustment": "Full bust adjustment",
                }
            ],
            "primary_recommendation": "Perform a full bust adjustment",
            "cascade_type": cascade_type,
        }
    )


def _build_client() -> TestClient:
    """Build a TestClient for the FastAPI app."""
    from main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /diagnosis/run — 200 happy path
# ---------------------------------------------------------------------------


class TestDiagnosisRunHappyPath:
    def test_200_with_valid_request_and_canned_outputs(self, tmp_path: Path) -> None:
        """POST /diagnosis/run returns 200 with DiagnosisResult shape when agent is patched."""
        # Set up a fake photo store
        measurement_id = "test-measurement-1"
        photo_id = "photo-abc-123"
        photo_dir = tmp_path / "photos" / measurement_id
        photo_dir.mkdir(parents=True)
        # Create the original photo file
        photo_file = photo_dir / f"{photo_id}.jpg"
        photo_file.write_bytes(b"fake jpg data")
        # Create the segmented crop file
        seg_dir = photo_dir / "segmented"
        seg_dir.mkdir()
        crop_file = seg_dir / f"{photo_id}_cropped.png"
        crop_file.write_bytes(b"\x89PNG\r\n\x1a\nfake crop")

        bust_json = _make_specialist_json("bust")
        waist_json = _make_specialist_json("waist_hip")
        back_json = _make_specialist_json("back")
        coordinator_json = _make_coordinator_json("fba")

        mock_agent = MagicMock()
        mock_agent.run.side_effect = [
            _make_agent_response(bust_json),
            _make_agent_response(waist_json),
            _make_agent_response(back_json),
            _make_agent_response(coordinator_json),
        ]

        client = _build_client()

        with (
            patch("routes.diagnosis.get_agent", return_value=mock_agent),
            patch("routes.diagnosis._BASE_DIR", tmp_path),
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
        ):
            response = client.post(
                "/diagnosis/run",
                json={"measurement_id": measurement_id, "photo_ids": [photo_id]},
            )

        assert response.status_code == 200
        data = response.json()
        assert "issues" in data
        assert "primary_recommendation" in data
        assert "cascade_type" in data
        assert data["cascade_type"] in {"fba", "swayback", "none"}


# ---------------------------------------------------------------------------
# POST /diagnosis/run — 404 cases
# ---------------------------------------------------------------------------


class TestDiagnosisRunNotFound:
    def test_404_unknown_measurement_id(self, tmp_path: Path) -> None:
        """Unknown measurement_id returns 404 with detail='Photo not found'."""
        client = _build_client()

        with (
            patch("routes.diagnosis._BASE_DIR", tmp_path),
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
        ):
            response = client.post(
                "/diagnosis/run",
                json={"measurement_id": "nonexistent-session", "photo_ids": ["any-photo-id"]},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Photo not found"

    def test_404_photo_id_with_no_segmented_crop(self, tmp_path: Path) -> None:
        """A photo_id that exists but has no segmented crop returns 404."""
        measurement_id = "test-session-2"
        photo_id = "photo-no-crop"
        photo_dir = tmp_path / "photos" / measurement_id
        photo_dir.mkdir(parents=True)
        # Create original photo but NO segmented crop
        photo_file = photo_dir / f"{photo_id}.jpg"
        photo_file.write_bytes(b"fake jpg data")

        client = _build_client()

        with (
            patch("routes.diagnosis._BASE_DIR", tmp_path),
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
        ):
            response = client.post(
                "/diagnosis/run",
                json={"measurement_id": measurement_id, "photo_ids": [photo_id]},
            )

        assert response.status_code == 404
        assert response.json()["detail"] == "Photo not found"


# ---------------------------------------------------------------------------
# POST /diagnosis/run — 500 case
# ---------------------------------------------------------------------------


class TestDiagnosisRunConfigError:
    def test_500_anthropic_api_key_not_set(self, tmp_path: Path) -> None:
        """Returns 500 with detail='ANTHROPIC_API_KEY not configured' when key is absent."""
        measurement_id = "test-session-3"
        photo_id = "photo-key-missing"
        photo_dir = tmp_path / "photos" / measurement_id
        photo_dir.mkdir(parents=True)
        photo_file = photo_dir / f"{photo_id}.jpg"
        photo_file.write_bytes(b"fake jpg data")
        seg_dir = photo_dir / "segmented"
        seg_dir.mkdir()
        crop_file = seg_dir / f"{photo_id}_cropped.png"
        crop_file.write_bytes(b"\x89PNG\r\n\x1a\nfake crop")

        from lib.diagnosis.agent import ConfigError

        mock_agent = MagicMock()
        mock_agent.run.side_effect = ConfigError("ANTHROPIC_API_KEY is not configured.")

        client = _build_client()

        with (
            patch("routes.diagnosis.get_agent", return_value=mock_agent),
            patch("routes.diagnosis._BASE_DIR", tmp_path),
        ):
            env = os.environ.copy()
            env.pop("ANTHROPIC_API_KEY", None)
            with patch.dict(os.environ, env, clear=True):
                response = client.post(
                    "/diagnosis/run",
                    json={"measurement_id": measurement_id, "photo_ids": [photo_id]},
                )

        assert response.status_code == 500
        assert response.json()["detail"] == "ANTHROPIC_API_KEY not configured"


# ---------------------------------------------------------------------------
# POST /diagnosis/run — 502 case
# ---------------------------------------------------------------------------


class TestDiagnosisRunServiceError:
    def test_502_all_specialists_failed_error(self, tmp_path: Path) -> None:
        """AllSpecialistsFailedError returns 502 with detail='Diagnosis service error'."""
        measurement_id = "test-session-4"
        photo_id = "photo-all-fail"
        photo_dir = tmp_path / "photos" / measurement_id
        photo_dir.mkdir(parents=True)
        photo_file = photo_dir / f"{photo_id}.jpg"
        photo_file.write_bytes(b"fake jpg data")
        seg_dir = photo_dir / "segmented"
        seg_dir.mkdir()
        crop_file = seg_dir / f"{photo_id}_cropped.png"
        crop_file.write_bytes(b"\x89PNG\r\n\x1a\nfake crop")

        mock_agent = MagicMock()
        mock_agent.run.side_effect = RuntimeError("all fail")

        client = _build_client()

        with (
            patch("routes.diagnosis.get_agent", return_value=mock_agent),
            patch("routes.diagnosis._BASE_DIR", tmp_path),
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
        ):
            response = client.post(
                "/diagnosis/run",
                json={"measurement_id": measurement_id, "photo_ids": [photo_id]},
            )

        assert response.status_code == 502
        assert response.json()["detail"] == "Diagnosis service error"

    def test_502_coordinator_parse_error(self, tmp_path: Path) -> None:
        """CoordinatorParseError returns 502 with detail='Diagnosis service error'."""
        measurement_id = "test-session-5"
        photo_id = "photo-coord-fail"
        photo_dir = tmp_path / "photos" / measurement_id
        photo_dir.mkdir(parents=True)
        photo_file = photo_dir / f"{photo_id}.jpg"
        photo_file.write_bytes(b"fake jpg data")
        seg_dir = photo_dir / "segmented"
        seg_dir.mkdir()
        crop_file = seg_dir / f"{photo_id}_cropped.png"
        crop_file.write_bytes(b"\x89PNG\r\n\x1a\nfake crop")

        bust_json = _make_specialist_json("bust")
        waist_json = _make_specialist_json("waist_hip")
        back_json = _make_specialist_json("back")
        bad_coordinator = '{"issues": [], "primary_recommendation": "ok", "cascade_type": "banana"}'

        mock_agent = MagicMock()
        mock_agent.run.side_effect = [
            _make_agent_response(bust_json),
            _make_agent_response(waist_json),
            _make_agent_response(back_json),
            _make_agent_response(bad_coordinator),
        ]

        client = _build_client()

        with (
            patch("routes.diagnosis.get_agent", return_value=mock_agent),
            patch("routes.diagnosis._BASE_DIR", tmp_path),
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}),
        ):
            response = client.post(
                "/diagnosis/run",
                json={"measurement_id": measurement_id, "photo_ids": [photo_id]},
            )

        assert response.status_code == 502
        assert response.json()["detail"] == "Diagnosis service error"


# ---------------------------------------------------------------------------
# POST /diagnosis/run — 422 validation errors
# ---------------------------------------------------------------------------


class TestDiagnosisRunValidationErrors:
    def test_422_empty_photo_ids(self) -> None:
        """photo_ids=[] returns 422."""
        client = _build_client()
        response = client.post(
            "/diagnosis/run",
            json={"measurement_id": "some-id", "photo_ids": []},
        )
        assert response.status_code == 422

    def test_422_photo_ids_too_many(self) -> None:
        """photo_ids with 4 items returns 422."""
        client = _build_client()
        response = client.post(
            "/diagnosis/run",
            json={
                "measurement_id": "some-id",
                "photo_ids": ["a", "b", "c", "d"],
            },
        )
        assert response.status_code == 422

    def test_422_missing_measurement_id(self) -> None:
        """Missing measurement_id field returns 422."""
        client = _build_client()
        response = client.post(
            "/diagnosis/run",
            json={"photo_ids": ["a"]},
        )
        assert response.status_code == 422
