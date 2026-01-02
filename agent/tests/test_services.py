"""Tests for custom services."""

import pytest

from voice_agent.services.chatterbox import ChatterboxTTSService


class TestChatterboxService:
    """Tests for Chatterbox TTS service."""

    def test_init_defaults(self):
        """Test service initialization with defaults."""
        service = ChatterboxTTSService()

        assert service._base_url == "http://localhost:5000"
        assert service._voice == "default"
        assert service._exaggeration == 0.5
        assert service._model == "turbo"

    def test_init_custom(self):
        """Test service initialization with custom values."""
        service = ChatterboxTTSService(
            base_url="http://custom:8000",
            voice="custom_voice",
            exaggeration=0.8,
            model="original",
        )

        assert service._base_url == "http://custom:8000"
        assert service._voice == "custom_voice"
        assert service._exaggeration == 0.8
        assert service._model == "original"

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup closes session."""
        service = ChatterboxTTSService()
        await service.cleanup()
        assert service._session is None
