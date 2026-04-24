"""Tests for main.py dev router gating behaviour (spec 18-dev-router-hardening)."""

import importlib

import pytest
from fastapi.testclient import TestClient

import main


class TestDevRouterDefaultEnv:
    """When APP_ENV is unset (or any non-production value), dev routes are active."""

    def test_dev_reverse_string_returns_200_when_app_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /dev/reverse-string returns 200 when APP_ENV is not set."""
        monkeypatch.delenv("APP_ENV", raising=False)
        try:
            importlib.reload(main)
            client = TestClient(main.app)
            response = client.post("/dev/reverse-string", json={"input": "hello"})
            assert response.status_code == 200
        finally:
            monkeypatch.delenv("APP_ENV", raising=False)
            importlib.reload(main)

    def test_openapi_excludes_dev_paths_when_app_env_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OpenAPI schema at /openapi.json omits /dev/* paths when APP_ENV is unset."""
        monkeypatch.delenv("APP_ENV", raising=False)
        try:
            importlib.reload(main)
            client = TestClient(main.app)
            response = client.get("/openapi.json")
            assert response.status_code == 200
            paths = response.json().get("paths", {})
            dev_paths = [p for p in paths if p.startswith("/dev/")]
            assert dev_paths == [], f"Expected no /dev/* paths in schema, found: {dev_paths}"
        finally:
            monkeypatch.delenv("APP_ENV", raising=False)
            importlib.reload(main)

    def test_dev_reverse_string_returns_200_when_app_env_development(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /dev/reverse-string returns 200 when APP_ENV='development'."""
        monkeypatch.setenv("APP_ENV", "development")
        try:
            importlib.reload(main)
            client = TestClient(main.app)
            response = client.post("/dev/reverse-string", json={"input": "hello"})
            assert response.status_code == 200
        finally:
            monkeypatch.delenv("APP_ENV", raising=False)
            importlib.reload(main)

    def test_openapi_excludes_dev_paths_when_app_env_development(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OpenAPI schema omits /dev/* paths even when APP_ENV='development'."""
        monkeypatch.setenv("APP_ENV", "development")
        try:
            importlib.reload(main)
            client = TestClient(main.app)
            response = client.get("/openapi.json")
            assert response.status_code == 200
            paths = response.json().get("paths", {})
            dev_paths = [p for p in paths if p.startswith("/dev/")]
            assert dev_paths == [], f"Expected no /dev/* paths in schema, found: {dev_paths}"
        finally:
            monkeypatch.delenv("APP_ENV", raising=False)
            importlib.reload(main)


class TestDevRouterProductionEnv:
    """When APP_ENV='production', dev routes are not registered."""

    def test_dev_reverse_string_returns_404_when_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /dev/reverse-string returns 404 when APP_ENV='production'."""
        monkeypatch.setenv("APP_ENV", "production")
        try:
            importlib.reload(main)
            client = TestClient(main.app)
            response = client.post("/dev/reverse-string", json={"input": "hello"})
            assert response.status_code == 404
        finally:
            monkeypatch.delenv("APP_ENV", raising=False)
            importlib.reload(main)

    def test_openapi_excludes_dev_paths_when_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OpenAPI schema omits /dev/* paths when APP_ENV='production'."""
        monkeypatch.setenv("APP_ENV", "production")
        try:
            importlib.reload(main)
            client = TestClient(main.app)
            response = client.get("/openapi.json")
            assert response.status_code == 200
            paths = response.json().get("paths", {})
            dev_paths = [p for p in paths if p.startswith("/dev/")]
            assert dev_paths == [], f"Expected no /dev/* paths in schema, found: {dev_paths}"
        finally:
            monkeypatch.delenv("APP_ENV", raising=False)
            importlib.reload(main)
