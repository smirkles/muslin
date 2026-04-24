"""Integration tests for POST /dev/reverse-string using FastAPI TestClient."""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestDevReverseStringRoute:
    def test_valid_input_returns_reversed(self) -> None:
        response = client.post("/dev/reverse-string", json={"input": "hello"})
        assert response.status_code == 200
        assert response.json() == {"result": "olleh"}

    def test_empty_string_returns_empty(self) -> None:
        response = client.post("/dev/reverse-string", json={"input": ""})
        assert response.status_code == 200
        assert response.json() == {"result": ""}

    def test_unicode_string_returns_reversed(self) -> None:
        response = client.post("/dev/reverse-string", json={"input": "café"})
        assert response.status_code == 200
        assert response.json() == {"result": "éfac"}

    def test_missing_input_field_returns_422(self) -> None:
        response = client.post("/dev/reverse-string", json={"wrong_key": "hello"})
        assert response.status_code == 422

    def test_malformed_json_returns_422(self) -> None:
        response = client.post(
            "/dev/reverse-string",
            content=b"not-json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self) -> None:
        response = client.post("/dev/reverse-string", json={})
        assert response.status_code == 422

    def test_numeric_input_returns_422(self) -> None:
        # Pydantic coerces numbers to str in v2 by default; we use strict mode
        # so a number passed as `input` should be rejected with 422.
        response = client.post("/dev/reverse-string", json={"input": 42})
        assert response.status_code == 422
