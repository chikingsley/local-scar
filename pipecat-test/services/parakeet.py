"""Parakeet STT service for Pipecat using onnx-asr.

Uses NVIDIA's Parakeet TDT model via onnx-asr for fast, accurate
local speech-to-text without external dependencies.

Performance:
- ~50ms per segment on GPU
- 6% WER (vs ~10% for Whisper)
- Supports audio up to 24 minutes
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from datetime import UTC

import numpy as np
from pipecat.frames.frames import ErrorFrame, Frame, TranscriptionFrame
from pipecat.services.stt_service import STTService

logger = logging.getLogger(__name__)


class ParakeetSTTService(STTService):
    """Local Parakeet STT using onnx-asr.

    Uses the Parakeet TDT v3 model for fast, accurate transcription.
    Works with Pipecat's VAD - audio segments are transcribed after
    voice activity ends.

    Args:
        model: Model name (default: nemo-parakeet-tdt-0.6b-v3)
        device: Inference device (cpu, cuda)
        quantization: Model quantization (None, int8)
        sample_rate: Expected audio sample rate (default: 16000)
    """

    def __init__(
        self,
        *,
        model: str = "nemo-parakeet-tdt-0.6b-v3",
        device: str = "cuda",
        quantization: str | None = None,
        sample_rate: int = 16000,
        **kwargs,
    ):
        super().__init__(sample_rate=sample_rate, **kwargs)
        self._model_name = model
        self._device = device
        self._quantization = quantization
        self._model = None
        self._loading = False

    async def start(self, frame):
        """Load the model on pipeline start."""
        await super().start(frame)
        await self._ensure_model()

    def _get_providers(self) -> list[str]:
        """Get ONNX Runtime execution providers based on device setting."""
        if self._device == "cuda":
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        elif self._device == "coreml":
            return ["CoreMLExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]

    async def _ensure_model(self):
        """Lazy-load the onnx-asr model."""
        if self._model is not None or self._loading:
            return

        self._loading = True
        try:
            import onnx_asr

            logger.info(f"Loading Parakeet model: {self._model_name} ({self._device})")
            start = time.time()

            # onnx-asr handles model download from HuggingFace
            self._model = onnx_asr.load_model(
                self._model_name,
                quantization=self._quantization,
                providers=self._get_providers(),
            )

            elapsed = time.time() - start
            logger.info(f"Parakeet model loaded in {elapsed:.1f}s")

        except ImportError:
            logger.error("onnx-asr not installed. Run: pip install onnx-asr[gpu,hub]")
            raise
        except Exception as e:
            logger.error(f"Failed to load Parakeet model: {e}")
            raise
        finally:
            self._loading = False

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        """Transcribe audio segment using Parakeet.

        Args:
            audio: Raw 16-bit signed PCM audio bytes

        Yields:
            TranscriptionFrame with transcribed text
        """
        if self._model is None:
            await self._ensure_model()

        if self._model is None:
            yield ErrorFrame("Parakeet model not loaded")
            return

        if not audio:
            return

        try:
            # Convert 16-bit PCM to float32 normalized [-1, 1]
            audio_int16 = np.frombuffer(audio, dtype=np.int16)
            audio_float = audio_int16.astype(np.float32) / 32768.0

            # onnx-asr expects numpy array at 16kHz
            start = time.time()
            result = self._model.recognize(audio_float)
            elapsed = time.time() - start

            # Result could be string or TextResults object
            text = str(result).strip() if result else ""

            if text:
                logger.debug(f"Parakeet transcribed ({elapsed*1000:.0f}ms): {text[:50]}...")
                yield TranscriptionFrame(
                    text=text,
                    user_id=self._user_id,
                    timestamp=self._timestamp_str(),
                    language="en",
                )
            else:
                logger.debug(f"Parakeet: no speech detected ({elapsed*1000:.0f}ms)")

        except Exception as e:
            logger.error(f"Parakeet transcription error: {e}")
            yield ErrorFrame(f"Transcription failed: {e}")

    def _timestamp_str(self) -> str:
        """Get ISO8601 timestamp."""
        from datetime import datetime

        return datetime.now(UTC).isoformat()

    async def cleanup(self):
        """Clean up model resources."""
        self._model = None
        await super().cleanup()
