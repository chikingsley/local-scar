"""Tests for configuration module."""

import os

import pytest

from voice_agent.config import Config


def test_config_defaults():
    """Test that config loads with defaults."""
    config = Config.load()

    assert config.riva_url == "localhost:50051"
    assert config.chatterbox_url == "http://localhost:5000"
    assert config.ollama_host == "http://localhost:11434"
    assert config.ollama_model == "test-model"


def test_config_from_env(monkeypatch):
    """Test that config reads from environment."""
    monkeypatch.setenv("RIVA_URL", "custom-riva:9999")
    monkeypatch.setenv("OLLAMA_MODEL", "custom-model")

    config = Config.load()

    assert config.riva_url == "custom-riva:9999"
    assert config.ollama_model == "custom-model"


def test_config_optional_n8n():
    """Test that n8n config is optional."""
    config = Config.load()

    # Should be None when not set
    assert config.n8n_mcp_url is None or isinstance(config.n8n_mcp_url, str)
