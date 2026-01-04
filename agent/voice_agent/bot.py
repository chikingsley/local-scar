"""Voice Agent - Main Pipecat bot with SmallWebRTC transport.

Usage:
    python -m voice_agent.bot

Environment:
    STT_MODEL         - Parakeet model (default: nemo-parakeet-tdt-0.6b-v3)
    STT_DEVICE        - Inference device (default: cuda)
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
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.request_handler import (
    SmallWebRTCRequest,
    SmallWebRTCRequestHandler,
)
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

from .config import settings
from .integrations import (
    WebSearchTool,
    discover_n8n_workflows,
    execute_n8n_workflow,
    initialize_mcp_servers,
    load_mcp_config,
)
from .services.chatterbox import ChatterboxTTSService
from .services.parakeet import ParakeetSTTService
from .webhooks import app as webhooks_app

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

# Global state for MCP sessions and workflow mappings
_mcp_sessions: dict[str, Any] = {}
_workflow_name_map: dict[str, str] = {}
_web_search_tool: WebSearchTool | None = None


def load_system_prompt() -> str:
    """Load system prompt from file."""
    prompt_file = settings.prompts_dir / "default.md"
    if prompt_file.exists():
        return prompt_file.read_text()
    return "You are a helpful voice assistant. Be concise and conversational."


async def load_tools() -> tuple[ToolsSchema, list[FunctionSchema]]:
    """Load all available tools (web search + n8n workflows).

    Returns:
        Tuple of (ToolsSchema for LLM, list of FunctionSchema for registration)
    """
    global _mcp_sessions, _workflow_name_map, _web_search_tool

    function_schemas: list[FunctionSchema] = []

    # 1. Web search tool (always available)
    _web_search_tool = WebSearchTool()
    web_search_schema = FunctionSchema(
        name="web_search",
        description="Search the web for current information. Use when you need up-to-date info about news, weather, events, or facts you're unsure about.",
        properties={
            "query": {
                "type": "string",
                "description": "The search query",
            },
        },
        required=["query"],
    )
    function_schemas.append(web_search_schema)
    logger.info("  ✓ web_search")

    # 2. n8n workflows via MCP (if configured)
    if settings.n8n_mcp_url:
        try:
            # Load and initialize MCP servers
            mcp_configs = load_mcp_config()
            _mcp_sessions = await initialize_mcp_servers(mcp_configs)

            if "n8n" in _mcp_sessions:
                # Discover workflows and create tool definitions
                n8n_base = settings.n8n_mcp_url.rsplit("/", 2)[0]  # Strip /mcp-server/http
                n8n_tools, _workflow_name_map = await discover_n8n_workflows(
                    _mcp_sessions["n8n"], n8n_base
                )

                # Convert n8n tools to FunctionSchema
                for tool in n8n_tools:
                    func = tool["function"]
                    schema = FunctionSchema(
                        name=func["name"],
                        description=func["description"],
                        properties=func["parameters"].get("properties", {}),
                        required=func["parameters"].get("required", []),
                    )
                    function_schemas.append(schema)

        except Exception as e:
            logger.warning(f"Failed to load n8n tools: {e}")

    if not function_schemas:
        logger.info("  No tools loaded")

    return ToolsSchema(standard_tools=function_schemas), function_schemas


def register_tool_handlers(llm: OLLamaLLMService) -> None:
    """Register function call handlers on the LLM service."""
    global _workflow_name_map, _web_search_tool

    # Web search handler
    async def handle_web_search(params: FunctionCallParams):
        query = params.arguments.get("query", "")
        if _web_search_tool and query:
            result = await _web_search_tool.search(query)
            await params.result_callback({"result": result})
        else:
            await params.result_callback({"error": "No query provided"})

    llm.register_function("web_search", handle_web_search)

    # n8n workflow handlers
    for tool_name, workflow_name in _workflow_name_map.items():

        async def handle_workflow(
            params: FunctionCallParams, wf_name: str = workflow_name
        ):
            try:
                n8n_base = settings.n8n_mcp_url.rsplit("/", 2)[0] if settings.n8n_mcp_url else ""
                result = await execute_n8n_workflow(n8n_base, wf_name, params.arguments)
                await params.result_callback(result)
            except Exception as e:
                logger.error(f"Workflow {wf_name} failed: {e}")
                await params.result_callback({"error": str(e)})

        llm.register_function(tool_name, handle_workflow)
        logger.debug(f"Registered handler for {tool_name} -> {workflow_name}")


async def create_pipeline(
    connection: SmallWebRTCConnection,
) -> tuple[PipelineTask, PipelineRunner]:
    """Create the voice bot pipeline for a connection.

    Pipeline flow:
        Transport Input → VAD → STT → LLM → TTS → Transport Output
    """
    logger.info("Creating voice bot pipeline...")
    logger.info(f"  STT: Parakeet ({settings.stt_model}) on {settings.stt_device}")
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
    stt = ParakeetSTTService(
        model=settings.stt_model,
        device=settings.stt_device,
        quantization=settings.stt_quantization,
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

    # Load tools (web search + n8n workflows)
    logger.info("Loading tools...")
    tools_schema, _ = await load_tools()

    # Register tool handlers on the LLM
    register_tool_handlers(llm)

    # LLM context with system prompt and tools
    system_prompt = load_system_prompt()
    context = OpenAILLMContext(
        messages=[{"role": "system", "content": system_prompt}],
        tools=tools_schema.standard_tools,
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
    from .webhooks import register_session, unregister_session

    data = await request.json()
    webrtc_request = SmallWebRTCRequest.from_dict(data)

    async def on_connection(connection: SmallWebRTCConnection):
        """Callback when WebRTC connection is established."""
        session_id = connection.pc_id
        logger.info(f"Client connected: {session_id}")

        task, runner = await create_pipeline(connection)

        # Register session for webhook access
        register_session(session_id, task)

        try:
            await runner.run(task)
        finally:
            # Clean up session on disconnect
            unregister_session(session_id)
            logger.info(f"Client disconnected: {session_id}")

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
    logger.info(f"Webhooks on port {settings.webhook_port}")

    # Main bot server (WebRTC signaling)
    bot_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.webrtc_port,
        log_level="info",
    )
    bot_server = uvicorn.Server(bot_config)

    # Webhooks server
    webhook_config = uvicorn.Config(
        webhooks_app,
        host="0.0.0.0",
        port=settings.webhook_port,
        log_level="info",
    )
    webhook_server = uvicorn.Server(webhook_config)

    # Run both servers concurrently
    await asyncio.gather(
        bot_server.serve(),
        webhook_server.serve(),
    )


def main():
    """Entry point."""
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
