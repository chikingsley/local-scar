# Voice Agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Pipecat](https://img.shields.io/badge/Pipecat-Framework-blue.svg)](https://github.com/pipecat-ai/pipecat)

**Local voice assistant with n8n workflow integration via MCP**

Built on [Pipecat](https://github.com/pipecat-ai/pipecat) with fully local STT/TTS/LLM using Parakeet (NVIDIA NeMo STT), [Chatterbox](https://github.com/devnen/chatterbox-tts-server) (TTS with voice cloning), and [Ollama](https://ollama.ai/).

## Features

- **Local Voice Pipeline**: Parakeet STT (ONNX) + Chatterbox TTS + Ollama LLM
- **SmallWebRTC**: Direct browser-to-agent WebRTC - no signaling server required
- **Wake Word Detection**: "Jarvis" activation via Picovoice Porcupine (configurable)
- **n8n Integrations**: Home Assistant, APIs, databases - anything n8n can connect to
- **Web Search**: DuckDuckGo integration for real-time information
- **Webhook API**: External triggers for announcements, wake, and tool reload
- **Mobile App**: Flutter client for Android (see `mobile/`)

## Quick Start (Docker)

```bash
# Clone and configure
git clone https://github.com/yourusername/voice-agent.git
cd voice-agent
cp .env.example .env
nano .env  # Set OLLAMA_HOST, N8N_MCP_URL, N8N_MCP_TOKEN (optional)

# Deploy
docker compose up -d
```

Open `http://localhost:3000` in your browser.

**Requirements (NVIDIA GPU):**
- Docker with [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [Ollama](https://ollama.ai/) running on your network
- [n8n](https://n8n.io/) with MCP enabled (optional, for workflow tools)
- 8GB+ VRAM recommended (Parakeet + Chatterbox share GPU)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Docker Compose Stack                                               │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Frontend   │  │    Agent     │  │  Chatterbox  │               │
│  │ (Vite+React) │  │  (Pipecat)   │  │    (TTS)     │               │
│  │    :3000     │  │ :8765 :8889  │  │    :5000     │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
│         │                 │                 │                       │
│         │  WebRTC         │  HTTP           │                       │
│         └─────────────────┤                 │                       │
│                           │                 │                       │
│                     ┌─────┴─────────────────┴─────┐                 │
│                     │      Voice Pipeline         │                 │
│                     │  ┌───────────────────────┐  │                 │
│                     │  │ Input → VAD → STT →   │  │                 │
│                     │  │ LLM → TTS → Output    │  │                 │
│                     │  └───────────────────────┘  │                 │
│                     │   Parakeet STT (in-process) │                 │
│                     └─────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
            ┌─────┴─────┐     ┌─────┴─────┐     ┌─────┴─────┐
            │  Ollama   │     │    n8n    │     │   Your    │
            │   (LLM)   │     │ Workflows │     │   APIs    │
            └───────────┘     └───────────┘     └───────────┘
                   External Services (on your network)
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Vite + React web UI |
| Agent | 8765 | WebRTC signaling (SmallWebRTC) |
| Agent | 8889 | Webhook API (announce, wake, reload) |
| Chatterbox | 5000 | TTS with voice cloning |

## Configuration

### Environment Variables (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `STT_MODEL` | Parakeet model name | `nemo-parakeet-tdt-0.6b-v3` |
| `STT_DEVICE` | STT device (cuda/cpu) | `cuda` |
| `TTS_VOICE` | Chatterbox voice | `default` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | LLM model name | `qwen3:8b` |
| `N8N_MCP_URL` | n8n MCP server URL (optional) | - |
| `N8N_MCP_TOKEN` | n8n MCP access token (optional) | - |
| `PORCUPINE_ACCESS_KEY` | Picovoice key for wake word | - |

## Web UI Settings

The web frontend includes a settings modal (gear icon) where you can configure:

- **Agent URL**: WebRTC signaling endpoint (default: `http://localhost:8765`)
- **Webhook URL**: Webhook API endpoint (default: `http://localhost:8889`)
- **Picovoice Access Key**: For wake word detection

Settings are stored in browser localStorage and persist across sessions.

## Wake Word Detection

The web UI supports "Jarvis" wake word detection using Picovoice Porcupine.

**Setup:**
1. Get a free access key from [Picovoice Console](https://console.picovoice.ai/)
2. Enter the key in the web UI settings (gear icon)
3. Enable wake word on the welcome screen

**Usage:**
- Say "Jarvis" to start a conversation
- The UI will automatically connect and begin listening

## n8n Workflow Integration

Voice Agent discovers tools from n8n workflows via MCP. Each workflow with a webhook trigger becomes a voice command.

### Setup n8n

1. Enable MCP in n8n: **Settings > MCP Access > Enable MCP**
2. Set connection method to **Access Token** and copy the token
3. Enable workflow access in each workflow's settings
4. Set `N8N_MCP_URL` and `N8N_MCP_TOKEN` in `.env`

### Example Workflows

| Workflow | Voice Command |
|----------|---------------|
| `espn_get_nfl_scores` | "What are the NFL scores?" |
| `calendar_get_events` | "What's on my calendar today?" |
| `hass_control` | "Turn on the office lamp" |

See `n8n-workflows/README.md` for workflow definitions.

## Webhook API

External systems can trigger Voice Agent actions via HTTP:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/announce` | POST | Make the agent speak a message |
| `/wake` | POST | Trigger wake greeting |
| `/reload-tools` | POST | Refresh MCP tool cache |
| `/health` | GET | Health check |

**Example - Announce:**
```bash
curl -X POST http://localhost:8889/announce \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123", "message": "Package delivered at front door"}'
```

## Mobile App

A Flutter mobile client is available in the `mobile/` directory for Android.

```bash
cd mobile
flutter pub get
flutter run
```

See `mobile/README.md` for setup instructions. Pre-built APKs are available in [GitHub Releases](https://github.com/yourusername/voice-agent/releases).

## Local Development

```bash
# Install Python dependencies
cd agent
uv sync

# Start TTS container
docker compose up -d chatterbox

# Run agent locally
uv run python -m voice_agent.bot

# In another terminal - run frontend
cd web
pnpm install
pnpm dev
```

**Development commands:**
```bash
cd agent
uv run ruff check voice_agent/   # Lint
uv run ty check voice_agent/     # Type check
uv run pytest                    # Test
```

## Project Structure

```
voice-agent/
├── agent/                      # Python voice agent
│   ├── voice_agent/
│   │   ├── bot.py              # Main Pipecat pipeline
│   │   ├── config.py           # Settings management
│   │   ├── webhooks.py         # HTTP webhook handlers
│   │   ├── services/           # STT/TTS service adapters
│   │   │   ├── parakeet.py     # Parakeet ONNX STT
│   │   │   └── chatterbox.py   # Chatterbox TTS client
│   │   └── integrations/       # n8n MCP, web search
│   ├── prompts/
│   │   └── default.md          # System prompt
│   ├── Dockerfile
│   └── pyproject.toml
├── web/                        # Vite + React frontend
│   ├── src/
│   │   ├── hooks/
│   │   │   ├── usePipecat.ts   # Pipecat WebRTC client
│   │   │   └── useWakeWord.ts  # Porcupine wake word
│   │   └── components/
│   ├── Dockerfile
│   └── package.json
├── mobile/                     # Flutter mobile app
├── n8n-workflows/              # Example n8n workflows
├── docker-compose.yaml         # Production deployment
└── .env.example                # Environment template
```

## Troubleshooting

### WebRTC Not Connecting

**Symptom**: Frontend loads but voice doesn't work

1. **Check agent is running**: `curl http://localhost:8765/health`
2. **Check browser console** for WebRTC errors
3. **Verify CORS**: Agent allows all origins by default

### Agent Not Processing Voice

```bash
# Check agent logs
docker compose logs -f agent

# Verify Chatterbox (TTS) is healthy
curl http://localhost:5000/health

# Verify Ollama is reachable
curl http://localhost:11434/api/tags
```

### Ollama Connection Failed

**Symptom**: Agent logs show "error connecting to Ollama"

Ollama defaults to localhost only. Start it with network binding:

```bash
OLLAMA_HOST=0.0.0.0 ollama serve
```

### First Start Is Slow

Normal - Parakeet model downloads on first run (~1.2GB). Watch with:
```bash
docker compose logs -f agent
```

### n8n Tools Not Loading

1. Verify `N8N_MCP_URL` and `N8N_MCP_TOKEN` in `.env`
2. Check n8n has MCP enabled (Settings > MCP Access)
3. Ensure workflows have webhook triggers and are active

## Migrating from CAAL (LiveKit)

This project is a migration from CAAL which used LiveKit Agents. Key differences:

| Feature | CAAL (old) | Voice Agent (new) |
|---------|------------|-------------------|
| Framework | LiveKit Agents | Pipecat |
| Transport | LiveKit Server | SmallWebRTC (direct) |
| STT | Speaches (Faster-Whisper) | Parakeet (ONNX) |
| TTS | Kokoro | Chatterbox |
| Frontend | Next.js | Vite + React |

The old CAAL code is preserved in `_archive/caal/` for reference.

## Related Projects

- [Pipecat](https://github.com/pipecat-ai/pipecat) - Voice agent framework
- [onnx-asr](https://github.com/your/onnx-asr) - ONNX runtime ASR (Parakeet)
- [Chatterbox TTS Server](https://github.com/devnen/chatterbox-tts-server) - TTS with voice cloning
- [Ollama](https://ollama.ai/) - Local LLM server
- [n8n](https://n8n.io/) - Workflow automation
- [Picovoice Porcupine](https://picovoice.ai/platform/porcupine/) - Wake word engine

## License

MIT License - see [LICENSE](LICENSE) for details.
