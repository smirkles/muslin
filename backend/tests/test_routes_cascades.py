"""Route tests for POST /cascades/apply-adjustment."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestSwaybackRoute:
    def test_valid_swayback_returns_200(self) -> None:
        """Valid swayback request returns 200."""
        response = client.post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "swayback", "amount_cm": 1.5},
        )
        assert response.status_code == 200

    def test_valid_swayback_returns_5_steps(self) -> None:
        """Valid swayback response has 5 steps."""
        response = client.post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "swayback", "amount_cm": 1.5},
        )
        body = response.json()
        assert len(body["steps"]) == 5

    def test_response_includes_seam_adjustments(self) -> None:
        """Response JSON includes seam_adjustments at top level."""
        response = client.post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "swayback", "amount_cm": 1.5},
        )
        body = response.json()
        assert "seam_adjustments" in body
        assert "cb_seam_delta_cm" in body["seam_adjustments"]

    def test_response_has_correct_adjustment_type(self) -> None:
        """Response adjustment_type matches request."""
        response = client.post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "swayback", "amount_cm": 1.5},
        )
        assert response.json()["adjustment_type"] == "swayback"

    def test_amount_too_small_returns_422(self) -> None:
        """amount_cm=0.3 returns 422 mentioning 0.5."""
        response = client.post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "swayback", "amount_cm": 0.3},
        )
        assert response.status_code == 422
        assert "0.5" in response.json()["detail"]

    def test_amount_too_large_returns_422(self) -> None:
        """amount_cm=3.0 returns 422 mentioning 2.5."""
        response = client.post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "swayback", "amount_cm": 3.0},
        )
        assert response.status_code == 422
        assert "2.5" in response.json()["detail"]

    def test_unknown_pattern_id_returns_404(self) -> None:
        """Unknown pattern_id returns 404."""
        response = client.post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "nonexistent", "adjustment_type": "swayback", "amount_cm": 1.5},
        )
        assert response.status_code == 404

    def test_unknown_adjustment_type_returns_400(self) -> None:
        """Unknown adjustment_type returns 400."""
        response = client.post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "unknown", "amount_cm": 1.5},
        )
        assert response.status_code == 400

    def test_steps_have_required_fields(self) -> None:
        """Each step has step_number, narration, and svg fields."""
        response = client.post(
            "/cascades/apply-adjustment",
            json={"pattern_id": "bodice-v1", "adjustment_type": "swayback", "amount_cm": 1.5},
        )
        for step in response.json()["steps"]:
            assert "step_number" in step
            assert "narration" in step
            assert "svg" in step
            assert len(step["narration"]) > 0
            assert "<svg" in step["svg"]
