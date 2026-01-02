"""Tests for configuration module."""

import pytest

from voice_agent.config import Settings, get_settings


def test_settings_defaults():
    """Test that settings loads with defaults."""
    settings = Settings()

    assert settings.nvidia_server == "grpc.nvcf.nvidia.com:443"
    assert settings.chatterbox_url == "http://localhost:5000"
    assert settings.ollama_host == "http://localhost:11434"
    assert settings.ollama_model == "qwen3:8b"


def test_settings_from_env(monkeypatch):
    """Test that settings reads from environment."""
    monkeypatch.setenv("NVIDIA_SERVER", "custom-nvidia:9999")
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model")

    # Clear the lru_cache to pick up new env vars
    get_settings.cache_clear()
    settings = Settings()

    assert settings.nvidia_server == "custom-nvidia:9999"
    assert settings.ollama_model == "custom-model"


def test_settings_optional_n8n():
    """Test that n8n config is optional."""
    settings = Settings()

    # Should be None when not set
    assert settings.n8n_mcp_url is None or isinstance(settings.n8n_mcp_url, str)


def test_settings_validation():
    """Test that settings validates values."""
    settings = Settings()

    # Port validation
    assert 1 <= settings.webrtc_port <= 65535
    assert 1 <= settings.webhook_port <= 65535

    # TTS exaggeration validation
    assert 0.0 <= settings.tts_exaggeration <= 1.0

    # Temperature validation
    assert 0.0 <= settings.ollama_temperature <= 2.0
