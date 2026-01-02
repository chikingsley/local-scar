"""Pytest configuration and fixtures."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from voice_agent.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear the settings cache before each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("NVIDIA_API_KEY", "test-api-key")
    monkeypatch.setenv("NVIDIA_SERVER", "grpc.nvcf.nvidia.com:443")
    monkeypatch.setenv("CHATTERBOX_URL", "http://localhost:5000")
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("WEBRTC_PORT", "8765")
    monkeypatch.setenv("WEBHOOK_PORT", "8889")


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client."""
    client = MagicMock()
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def sample_workflows():
    """Sample n8n workflow data for testing."""
    return {
        "data": [
            {"id": "1", "name": "test_workflow", "description": "Test workflow"},
            {"id": "2", "name": "another_workflow", "description": "Another test"},
        ],
        "count": 2,
    }


@pytest.fixture
def sample_workflow_details():
    """Sample workflow details with webhook node."""
    return {
        "workflow": {
            "nodes": [
                {
                    "type": "n8n-nodes-base.webhook",
                    "notes": "This workflow does something useful. Args: action (str), target (str)",
                }
            ]
        }
    }
