# Voice Agent

Local voice assistant powered by Pipecat with SmallWebRTC transport.

## Components

- **STT**: NVIDIA Riva with Parakeet
- **LLM**: Ollama (local models)
- **TTS**: Chatterbox with voice cloning
- **Transport**: SmallWebRTCTransport (p2p)
- **Integrations**: n8n MCP, DuckDuckGo search

## Setup

```bash
# Install dependencies
uv sync

# Copy and configure environment
cp .env.example .env

# Run the agent
uv run voice-agent
```

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Type check
uv run ty check voice_agent
```
