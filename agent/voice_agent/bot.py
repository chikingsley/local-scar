"""Voice Agent - Main Pipecat bot with SmallWebRTC transport.

Usage:
    python -m voice_agent.bot

Environment:
    NVIDIA_API_KEY    - NVIDIA API key for STT (get from build.nvidia.com)
    CHATTERBOX_URL    - Chatterbox TTS endpoint (default: http://localhost:5000)
    OLLAMA_HOST       - Ollama API endpoint (default: http://localhost:11434)
    OLLAMA_MODEL      - LLM model name (default: qwen3:8b)
    WEBRTC_PORT       - WebRTC signaling port (default: 8765)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.nvidia.stt import NvidiaSTTService
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

from .config import settings
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

# FastAPI app for WebRTC signaling
app = FastAPI(title="Voice Agent WebRTC Signaling")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebRTC request handler
request_handler = SmallWebRTCRequestHandler()


def load_system_prompt() -> str:
    """Load system prompt from file."""
    prompt_file = settings.prompts_dir / "default.md"
    if prompt_file.exists():
        return prompt_file.read_text()
    return "You are a helpful voice assistant. Be concise and conversational."


async def create_pipeline(
    connection: SmallWebRTCConnection,
) -> tuple[PipelineTask, PipelineRunner]:
    """Create the voice bot pipeline for a connection.

    Pipeline flow:
        Transport Input → VAD → STT → LLM → TTS → Transport Output
    """
    logger.info("Creating voice bot pipeline...")
    logger.info(f"  STT: NVIDIA @ {settings.nvidia_server}")
    logger.info(f"  LLM: Ollama @ {settings.ollama_host} ({settings.ollama_model})")
    logger.info(f"  TTS: Chatterbox @ {settings.chatterbox_url}")

    # Transport params
    params = TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        vad_enabled=True,
        vad_analyzer=SileroVADAnalyzer(),
    )

    # Create transport from connection
    transport = SmallWebRTCTransport(
        webrtc_connection=connection,
        params=params,
    )

    # Services
    stt = NvidiaSTTService(
        api_key=settings.nvidia_api_key,
        server=settings.nvidia_server,
    )

    llm = OLLamaLLMService(
        model=settings.ollama_model,
        base_url=settings.ollama_host,
    )

    tts = ChatterboxTTSService(
        base_url=settings.chatterbox_url,
        voice=settings.tts_voice,
        exaggeration=settings.tts_exaggeration,
    )

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

    runner = PipelineRunner()
    return task, runner


@app.post("/offer")
async def handle_offer(request: Request) -> dict[str, Any]:
    """Handle WebRTC offer from client."""
    data = await request.json()
    webrtc_request = SmallWebRTCRequest.from_dict(data)

    async def on_connection(connection: SmallWebRTCConnection):
        """Callback when WebRTC connection is established."""
        logger.info(f"Client connected: {connection.pc_id}")
        task, runner = await create_pipeline(connection)
        await runner.run(task)
        logger.info(f"Client disconnected: {connection.pc_id}")

    result = await request_handler.handle_web_request(webrtc_request, on_connection)
    return result or {}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


async def run_bot():
    """Run the voice bot server."""
    logger.info("=" * 60)
    logger.info("STARTING VOICE AGENT")
    logger.info("=" * 60)
    logger.info(f"WebRTC signaling on port {settings.webrtc_port}")

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.webrtc_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


def main():
    """Entry point."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
