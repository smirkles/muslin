"""Route tests for POST /dev/hello-agent.

Tests use a patched agent to avoid real API calls.
"""

from unittest.mock import MagicMock, patch

import anthropic
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _make_agent_response(
    text: str = "Hello Seamstress Steph!",
    model: str = "claude-opus-4-7",
    input_tokens: int = 10,
    output_tokens: int = 5,
) -> MagicMock:
    """Return a mock AgentResponse-like object."""
    from lib.diagnosis.agent import AgentResponse

    return AgentResponse(
        text=text,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


class TestHelloAgentRoute:
    def test_valid_request_returns_200_with_agent_response_shape(self) -> None:
        """POST /dev/hello-agent with valid body returns 200 and correct response shape."""
        mock_agent = MagicMock()
        mock_agent.run.return_value = _make_agent_response()

        with patch("routes.dev.get_agent", return_value=mock_agent):
            response = client.post("/dev/hello-agent", json={"name": "Steph"})

        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "Hello Seamstress Steph!"
        assert body["model"] == "claude-opus-4-7"
        assert body["input_tokens"] == 10
        assert body["output_tokens"] == 5

    def test_valid_request_calls_agent_with_correct_args(self) -> None:
        """Route calls agent.run with 'hello_world' prompt and the supplied name."""
        mock_agent = MagicMock()
        mock_agent.run.return_value = _make_agent_response()

        with patch("routes.dev.get_agent", return_value=mock_agent):
            client.post("/dev/hello-agent", json={"name": "Steph"})

        mock_agent.run.assert_called_once_with("hello_world", {"name": "Steph"})

    def test_empty_name_returns_422(self) -> None:
        """POST /dev/hello-agent with empty name returns 422."""
        response = client.post("/dev/hello-agent", json={"name": ""})
        assert response.status_code == 422

    def test_name_over_100_chars_returns_422(self) -> None:
        """POST /dev/hello-agent with name over 100 chars returns 422."""
        long_name = "a" * 101
        response = client.post("/dev/hello-agent", json={"name": long_name})
        assert response.status_code == 422

    def test_name_exactly_100_chars_returns_200(self) -> None:
        """POST /dev/hello-agent with name exactly 100 chars is accepted."""
        mock_agent = MagicMock()
        mock_agent.run.return_value = _make_agent_response()

        with patch("routes.dev.get_agent", return_value=mock_agent):
            response = client.post("/dev/hello-agent", json={"name": "a" * 100})

        assert response.status_code == 200

    def test_missing_name_field_returns_422(self) -> None:
        """POST /dev/hello-agent without name field returns 422."""
        response = client.post("/dev/hello-agent", json={})
        assert response.status_code == 422

    def test_missing_api_key_returns_500(self) -> None:
        """POST /dev/hello-agent returns 500 with the spec-documented detail string.

        The route must hardcode the detail — not pass through the exception message —
        so this test uses a different exception message to prove the contract holds
        regardless of what ConfigError contains.
        """
        from lib.diagnosis.agent import ConfigError

        mock_agent = MagicMock()
        mock_agent.run.side_effect = ConfigError("some long developer-facing message")

        with patch("routes.dev.get_agent", return_value=mock_agent):
            response = client.post("/dev/hello-agent", json={"name": "Steph"})

        assert response.status_code == 500
        assert response.json()["detail"] == "ANTHROPIC_API_KEY not configured"

    def test_anthropic_sdk_error_returns_502(self) -> None:
        """POST /dev/hello-agent returns 502 when the Anthropic SDK raises APIError."""
        mock_agent = MagicMock()
        mock_agent.run.side_effect = anthropic.APIStatusError(
            "auth failure",
            response=MagicMock(status_code=401),
            body={"error": {"type": "authentication_error", "message": "auth failure"}},
        )

        with patch("routes.dev.get_agent", return_value=mock_agent):
            response = client.post("/dev/hello-agent", json={"name": "Steph"})

        assert response.status_code == 502
        body = response.json()
        assert body["detail"] == "Claude API error"
        # Must not leak the original exception message
        assert "auth failure" not in body["detail"]

    def test_502_detail_does_not_leak_exception_message(self) -> None:
        """The 502 response detail must be generic, not the raw SDK exception text."""
        mock_agent = MagicMock()
        mock_agent.run.side_effect = anthropic.APIStatusError(
            "SUPER_SECRET_INTERNAL_ERROR",
            response=MagicMock(status_code=500),
            body={"error": {"type": "api_error", "message": "SUPER_SECRET_INTERNAL_ERROR"}},
        )

        with patch("routes.dev.get_agent", return_value=mock_agent):
            response = client.post("/dev/hello-agent", json={"name": "Steph"})

        assert response.status_code == 502
        assert "SUPER_SECRET_INTERNAL_ERROR" not in response.text

    def test_numeric_name_returns_422(self) -> None:
        """POST /dev/hello-agent with numeric name returns 422 (strict mode)."""
        response = client.post("/dev/hello-agent", json={"name": 42})
        assert response.status_code == 422
