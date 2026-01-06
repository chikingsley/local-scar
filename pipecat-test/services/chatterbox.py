"""Chatterbox TTS service for Pipecat.

Chatterbox-TTS-Server exposes an OpenAI-compatible /v1/audio/speech endpoint,
so we can use Pipecat's OpenAI TTS service with a custom base URL.

Features:
- Zero-shot voice cloning from reference audio
- Emotion control (exaggeration parameter)
- Paralinguistic tags: [laugh], [cough], [chuckle]
- 23 languages supported
"""

from __future__ import annotations

from typing import AsyncGenerator  # noqa: UP035 - must match TTSService base class

import aiohttp
from pipecat.frames.frames import AudioRawFrame, ErrorFrame, Frame
from pipecat.services.tts_service import TTSService


class ChatterboxTTSService(TTSService):
    """Chatterbox TTS service.

    Uses the Chatterbox-TTS-Server's OpenAI-compatible API.

    Args:
        base_url: Chatterbox server URL (e.g., http://localhost:5000)
        voice: Voice name or path to reference audio for cloning
        exaggeration: Emotion intensity (0.0 = monotone, 1.0 = expressive)
        model: Model variant ("turbo" or "original")
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:5000",
        voice: str = "default",
        exaggeration: float = 0.5,
        model: str = "turbo",
        sample_rate: int = 24000,
        **kwargs,
    ):
        super().__init__(sample_rate=sample_rate, **kwargs)
        self._base_url = base_url.rstrip("/")
        self._voice = voice
        self._exaggeration = exaggeration
        self._model = model
        self._session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """Convert text to speech using Chatterbox.

        Yields AudioRawFrame chunks as they're received.
        """
        if not text.strip():
            return

        session = await self._ensure_session()

        # Chatterbox TTS endpoint
        url = f"{self._base_url}/v1/audio/speech"

        payload = {
            "input": text,
            "voice": self._voice,
            "model": self._model,
            "response_format": "pcm",  # Raw PCM for streaming
            "exaggeration": self._exaggeration,
        }

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    yield ErrorFrame(f"Chatterbox TTS error: {response.status} - {error_text}")
                    return

                # Stream audio chunks
                async for chunk in response.content.iter_chunked(4096):
                    if chunk:
                        yield AudioRawFrame(
                            audio=chunk,
                            sample_rate=self._sample_rate,
                            num_channels=1,
                        )

        except aiohttp.ClientError as e:
            yield ErrorFrame(f"Chatterbox connection error: {e}")

    async def cleanup(self):
        """Clean up resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
