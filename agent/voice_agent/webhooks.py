"""Webhook server for external triggers.

Endpoints:
    POST /announce      - Make the agent speak a message
    POST /reload-tools  - Refresh MCP tool cache
    POST /wake          - Handle wake word detection
    GET  /health        - Health check
    GET  /voices        - List available TTS voices
    GET  /models        - List available LLM models
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pipecat.frames.frames import TTSSpeakFrame
from pydantic import BaseModel

from .config import settings

if TYPE_CHECKING:
    from pipecat.pipeline.task import PipelineTask

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Voice Agent Webhook API",
    description="External triggers for voice agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session registry: session_id -> PipelineTask
_sessions: dict[str, PipelineTask] = {}


def register_session(session_id: str, task: PipelineTask) -> None:
    """Register an active session with its pipeline task."""
    _sessions[session_id] = task
    logger.info(f"Session registered: {session_id}")


def unregister_session(session_id: str) -> None:
    """Unregister a session."""
    _sessions.pop(session_id, None)
    logger.info(f"Session unregistered: {session_id}")


def get_task(session_id: str) -> PipelineTask | None:
    """Get a pipeline task by session ID."""
    return _sessions.get(session_id)


def list_sessions() -> list[str]:
    """List active session IDs."""
    return list(_sessions.keys())


# Request/Response Models


class AnnounceRequest(BaseModel):
    message: str
    session_id: str = "default"


class AnnounceResponse(BaseModel):
    status: str
    session_id: str


class WakeRequest(BaseModel):
    session_id: str = "default"


class WakeResponse(BaseModel):
    status: str
    session_id: str


class ReloadToolsRequest(BaseModel):
    tool_name: str | None = None
    message: str | None = None
    session_id: str = "default"


class ReloadToolsResponse(BaseModel):
    status: str
    tool_count: int
    session_id: str


class HealthResponse(BaseModel):
    status: str
    active_sessions: list[str]


class VoicesResponse(BaseModel):
    voices: list[str]


class ModelsResponse(BaseModel):
    models: list[str]


# Endpoints


@app.post("/announce", response_model=AnnounceResponse)
async def announce(req: AnnounceRequest) -> AnnounceResponse:
    """Make the agent speak a message."""
    task = get_task(req.session_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"No active session: {req.session_id}",
        )

    logger.info(f"Announcing to {req.session_id}: {req.message[:50]}...")

    # Inject TTS frame into pipeline
    await task.queue_frames([TTSSpeakFrame(text=req.message)])

    return AnnounceResponse(status="announced", session_id=req.session_id)


@app.post("/wake", response_model=WakeResponse)
async def wake(req: WakeRequest) -> WakeResponse:
    """Handle wake word detection."""
    task = get_task(req.session_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"No active session: {req.session_id}",
        )

    logger.info(f"Wake word detected: {req.session_id}")

    greetings = [
        "Hey! What can I help you with?",
        "I'm here. What do you need?",
        "Yes? How can I help?",
        "What's up?",
    ]
    greeting = random.choice(greetings)

    # Inject greeting into pipeline
    await task.queue_frames([TTSSpeakFrame(text=greeting)])

    return WakeResponse(status="greeted", session_id=req.session_id)


@app.post("/reload-tools", response_model=ReloadToolsResponse)
async def reload_tools(req: ReloadToolsRequest) -> ReloadToolsResponse:
    """Refresh MCP tool cache."""
    task = get_task(req.session_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"No active session: {req.session_id}",
        )

    logger.info(f"Reloading tools for {req.session_id}")

    from .integrations import clear_caches

    clear_caches()

    # Count tools (would need to re-discover, simplified for now)
    tool_count = 0

    # Announce if requested
    if req.message:
        await task.queue_frames([TTSSpeakFrame(text=req.message)])
    elif req.tool_name:
        await task.queue_frames([
            TTSSpeakFrame(text=f"A new tool called {req.tool_name} is now available.")
        ])

    return ReloadToolsResponse(
        status="reloaded",
        tool_count=tool_count,
        session_id=req.session_id,
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        active_sessions=list_sessions(),
    )


@app.get("/voices", response_model=VoicesResponse)
async def get_voices() -> VoicesResponse:
    """Get available TTS voices from Chatterbox."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.chatterbox_url}/v1/voices",
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            voices = data.get("voices", [])
            return VoicesResponse(voices=voices)
    except Exception as e:
        logger.warning(f"Failed to fetch voices: {e}")
        return VoicesResponse(voices=["default"])


@app.get("/models", response_model=ModelsResponse)
async def get_models() -> ModelsResponse:
    """Get available LLM models from Ollama."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.ollama_host}/api/tags",
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            models = [m.get("name") for m in data.get("models", []) if m.get("name")]
            return ModelsResponse(models=models)
    except Exception as e:
        logger.warning(f"Failed to fetch models: {e}")
        return ModelsResponse(models=[])
