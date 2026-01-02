"""Tests for webhook API."""

import pytest
from fastapi.testclient import TestClient

from voice_agent.webhooks import app, register_session, unregister_session


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "active_sessions" in data


class TestAnnounceEndpoint:
    """Tests for announce endpoint."""

    def test_announce_no_session(self, client):
        """Test announce fails without active session."""
        response = client.post(
            "/announce",
            json={"message": "Hello", "session_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_announce_with_session(self, client):
        """Test announce succeeds with active session."""
        # Register a mock session
        register_session("test-session", object(), object())

        try:
            response = client.post(
                "/announce",
                json={"message": "Hello", "session_id": "test-session"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "announced"
        finally:
            unregister_session("test-session")


class TestWakeEndpoint:
    """Tests for wake word endpoint."""

    def test_wake_no_session(self, client):
        """Test wake fails without active session."""
        response = client.post(
            "/wake",
            json={"session_id": "nonexistent"},
        )
        assert response.status_code == 404


class TestReloadToolsEndpoint:
    """Tests for reload-tools endpoint."""

    def test_reload_no_session(self, client):
        """Test reload fails without active session."""
        response = client.post(
            "/reload-tools",
            json={"session_id": "nonexistent"},
        )
        assert response.status_code == 404


class TestVoicesEndpoint:
    """Tests for voices endpoint."""

    def test_get_voices_fallback(self, client):
        """Test voices endpoint returns fallback on error."""
        # Will fail to connect to Chatterbox, should return fallback
        response = client.get("/voices")
        assert response.status_code == 200
        assert "voices" in response.json()


class TestModelsEndpoint:
    """Tests for models endpoint."""

    def test_get_models_fallback(self, client):
        """Test models endpoint returns empty on error."""
        # Will fail to connect to Ollama, should return empty list
        response = client.get("/models")
        assert response.status_code == 200
        assert response.json()["models"] == []
