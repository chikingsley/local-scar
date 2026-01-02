"""Voice Agent - Main Pipecat bot with SmallWebRTC transport.

Usage:
    python -m voice_agent.bot

Environment:
    RIVA_URL          - Riva gRPC endpoint (default: localhost:50051)
    CHATTERBOX_URL    - Chatterbox TTS endpoint (default: http://localhost:5000)
    OLLAMA_HOST       - Ollama API endpoint (default: http://localhost:11434)
    OLLAMA_MODEL      - LLM model name (default: qwen3:8b)
    WEBRTC_PORT       - WebRTC signaling port (default: 8765)
    WEBHOOK_PORT      - Webhook API port (default: 8889)
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import EndFrame, TextFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.ollama import OllamaLLMService
from pipecat.services.riva import RivaSTTService
from pipecat.transports.services.small_webrtc import SmallWebRTCTransport

from .config import config
from .services.chatterbox import ChatterboxTTSService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def load_system_prompt() -> str:
    """Load system prompt from file."""
    prompt_file = config.prompts_dir / "default.md"
    if prompt_file.exists():
        return prompt_file.read_text()
    return "You are a helpful voice assistant. Be concise and conversational."


async def create_bot(transport: SmallWebRTCTransport) -> PipelineTask:
    """Create the voice bot pipeline.

    Pipeline flow:
        Transport Input → VAD → STT → LLM → TTS → Transport Output
    """
    logger.info("Creating voice bot pipeline...")
    logger.info(f"  STT: Riva @ {config.riva_url}")
    logger.info(f"  LLM: Ollama @ {config.ollama_host} ({config.ollama_model})")
    logger.info(f"  TTS: Chatterbox @ {config.chatterbox_url}")

    # Services
    stt = RivaSTTService(
        server=config.riva_url,
        language_code="en-US",
    )

    llm = OllamaLLMService(
        model=config.ollama_model,
        base_url=config.ollama_host,
    )

    tts = ChatterboxTTSService(
        base_url=config.chatterbox_url,
        voice=config.tts_voice,
    )

    # VAD for detecting speech
    vad = SileroVADAnalyzer()

    # LLM context with system prompt
    system_prompt = load_system_prompt()
    context = OpenAILLMContext(
        messages=[{"role": "system", "content": system_prompt}]
    )
    context_aggregator = llm.create_context_aggregator(context)

    # Build pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            vad,
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
        ),
    )

    return task


async def run_bot():
    """Run the voice bot server."""
    logger.info("=" * 60)
    logger.info("STARTING VOICE AGENT")
    logger.info("=" * 60)

    # Create WebRTC transport
    transport = SmallWebRTCTransport(
        host="0.0.0.0",
        port=config.webrtc_port,
    )

    logger.info(f"WebRTC signaling on port {config.webrtc_port}")

    # Create and run pipeline
    runner = PipelineRunner()

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client_id):
        logger.info(f"Client connected: {client_id}")
        task = await create_bot(transport)
        await runner.run(task)

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client_id):
        logger.info(f"Client disconnected: {client_id}")

    # Start transport (blocks until shutdown)
    await transport.run()


def main():
    """Entry point."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
