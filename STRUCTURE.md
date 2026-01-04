# Project Structure

## Current (CAAL/LiveKit) vs New (Pipecat)

### What Changes

| Current | New | Notes |
|---------|-----|-------|
| `voice_agent.py` | `agent/bot.py` | Rewrite with Pipecat pipeline |
| `frontend/` (Next.js) | `web/` (Vite+React) | New frontend, keep UI patterns |
| `docker-compose.yaml` | `docker-compose.yaml` | New services |
| `livekit.yaml` | (removed) | No LiveKit |
| `livekit-tailscale.yaml.template` | (removed) | No LiveKit |
| `nginx.conf` | (removed) | Not needed with SmallWebRTC |

### What Stays (Mostly)

| Keep | Migrate To | Notes |
|------|------------|-------|
| `src/caal/integrations/n8n.py` | `agent/integrations/n8n.py` | Same logic, works with any LLM |
| `src/caal/integrations/mcp_loader.py` | `agent/integrations/mcp.py` | Same logic |
| `src/caal/integrations/web_search.py` | `agent/integrations/web_search.py` | Same logic |
| `src/caal/webhooks.py` | `agent/webhooks.py` | Same FastAPI endpoints |
| `src/caal/settings.py` | `agent/settings.py` | Same logic |
| `prompt/default.md` | `agent/prompts/default.md` | Same prompts |
| `n8n-workflows/` | `n8n-workflows/` | Keep as-is |

## New Directory Structure

```
local-scar/
├── agent/                      # Python backend (Pipecat)
│   ├── __init__.py
│   ├── bot.py                  # Main Pipecat pipeline
│   ├── config.py               # Environment config
│   ├── webhooks.py             # FastAPI webhook server
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── n8n.py              # n8n workflow discovery
│   │   ├── mcp.py              # MCP server loader
│   │   └── web_search.py       # DuckDuckGo search
│   ├── prompts/
│   │   └── default.md          # System prompt
│   ├── Dockerfile
│   └── pyproject.toml
│
├── web/                        # Vite + React frontend
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── SessionView.tsx
│   │   │   ├── ControlBar.tsx
│   │   │   ├── ChatTranscript.tsx
│   │   │   ├── WakeWord.tsx
│   │   │   └── Settings.tsx
│   │   ├── hooks/
│   │   │   ├── usePipecat.ts   # Pipecat client hook
│   │   │   └── useWakeWord.ts  # Picovoice integration
│   │   └── lib/
│   │       └── utils.ts
│   ├── public/
│   │   └── hey_cal.ppn         # Wake word model
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   └── Dockerfile
│
├── mobile/                     # React Native app (later)
│   └── ...
│
├── n8n-workflows/              # Keep as-is
│   ├── setup.py
│   ├── config.env.example
│   └── *.json
│
├── docker-compose.yaml         # Main compose file
├── docker-compose.dev.yaml     # Dev overrides
├── .env.example
├── DECISIONS.md
├── STRUCTURE.md
└── README.md
```

## Docker Services

### docker-compose.yaml

```yaml
services:
  # ==========================================================================
  # Agent - Pipecat Voice Pipeline
  # ==========================================================================
  agent:
    build: ./agent
    ports:
      - "8889:8889"     # Webhooks
      - "8765:8765"     # WebRTC signaling (SmallWebRTC)
    environment:
      - RIVA_URL=riva:50051
      - CHATTERBOX_URL=http://chatterbox:5000
      - OLLAMA_HOST=http://host.docker.internal:11434
      - N8N_MCP_URL=${N8N_MCP_URL}
      - N8N_MCP_TOKEN=${N8N_MCP_TOKEN}
    extra_hosts:
      - "host.docker.internal:host-gateway"
    depends_on:
      - riva
      - chatterbox

  # ==========================================================================
  # Riva - NVIDIA STT (Parakeet)
  # ==========================================================================
  riva:
    image: nvcr.io/nvidia/riva/riva-speech:2.18.0
    ports:
      - "50051:50051"   # gRPC
      - "8001:8001"     # HTTP (optional)
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - riva-models:/data/models
    command: >
      riva-build --asr
      --decoder-type=ctc
      --language_code=en-US
      --model=parakeet-tdt-0.6b

  # ==========================================================================
  # Chatterbox - TTS with voice cloning
  # ==========================================================================
  chatterbox:
    image: ghcr.io/devnen/chatterbox-tts-server:latest
    ports:
      - "5000:5000"
    environment:
      - DEVICE=cuda
      - MODEL=turbo
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - chatterbox-cache:/app/cache
      - ./voices:/app/voices     # Reference audio for cloning

  # ==========================================================================
  # Frontend - Vite + React
  # ==========================================================================
  frontend:
    build: ./web
    ports:
      - "3000:3000"
    environment:
      - VITE_AGENT_URL=ws://localhost:8765
      - VITE_WEBHOOK_URL=http://localhost:8889
      - VITE_PORCUPINE_ACCESS_KEY=${PORCUPINE_ACCESS_KEY}

networks:
  default:
    driver: bridge

volumes:
  riva-models:
  chatterbox-cache:
```

## Pipecat Pipeline (agent/bot.py)

```python
from pipecat.frames.frames import EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.services.riva import RivaSTTService
from pipecat.services.ollama import OllamaLLMService
from pipecat.transports.small_webrtc import SmallWebRTCTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.turn.smart_turn.local import LocalSmartTurnAnalyzerV3

# Custom Chatterbox TTS service (OpenAI-compatible)
from .services.chatterbox import ChatterboxTTSService

async def create_pipeline(transport: SmallWebRTCTransport):
    """Create the voice pipeline."""

    # Services
    stt = RivaSTTService(
        url=os.getenv("RIVA_URL", "localhost:50051"),
        model="parakeet-tdt-0.6b",
    )

    llm = OllamaLLMService(
        model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    )

    tts = ChatterboxTTSService(
        base_url=os.getenv("CHATTERBOX_URL", "http://localhost:5000"),
        voice="default",  # or reference audio path for cloning
    )

    # VAD and turn detection
    vad = SileroVADAnalyzer()
    turn = LocalSmartTurnAnalyzerV3()

    # Pipeline: transport -> STT -> LLM -> TTS -> transport
    pipeline = Pipeline([
        transport.input(),
        vad,
        stt,
        turn,
        llm,
        tts,
        transport.output(),
    ])

    return PipelineTask(pipeline)
```

## Frontend (web/src/hooks/usePipecat.ts)

```typescript
import { PipecatClient } from '@pipecat-ai/client-js';
import { SmallWebRTCTransport } from '@pipecat-ai/small-webrtc-transport';

export function usePipecat() {
  const [client, setClient] = useState<PipecatClient | null>(null);
  const [state, setState] = useState<'idle' | 'connecting' | 'connected'>('idle');

  const connect = useCallback(async () => {
    setState('connecting');

    const transport = new SmallWebRTCTransport({
      url: import.meta.env.VITE_AGENT_URL,
    });

    const pipecatClient = new PipecatClient({
      transport,
    });

    await pipecatClient.connect();
    setClient(pipecatClient);
    setState('connected');
  }, []);

  const disconnect = useCallback(async () => {
    await client?.disconnect();
    setClient(null);
    setState('idle');
  }, [client]);

  return { client, state, connect, disconnect };
}
```

## Migration Checklist

### Phase 1: Core Pipeline
- [x] Set up Parakeet STT (via onnx-asr, local ONNX)
- [x] Set up Chatterbox container
- [x] Create Pipecat agent with SmallWebRTC
- [x] Wire MCP/n8n tools into LLM pipeline
- [x] Port webhook server (structure done, injection TODO)

### Phase 2: Frontend
- [x] Create Vite + React project
- [x] Implement Pipecat client connection (@pipecat-ai/client-js)
- [x] Port UI components (SessionView, ChatTranscript)
- [ ] Port Picovoice wake word

### Phase 3: Polish
- [ ] Implement webhook injection (announce/wake/reload)
- [ ] Port settings modal
- [ ] Port tool status indicator
- [ ] Add Tailscale configuration
- [ ] Update README

## Key Differences from CAAL

### Transport
```
CAAL:     Browser → LiveKit Server → Agent
Pipecat:  Browser → Agent (direct WebRTC)
```
No intermediary server = simpler, lower latency.

### STT Flow
```
CAAL:     Audio → Speaches (Whisper) → Text
Pipecat:  Audio → Riva (Parakeet) → Text
```
Parakeet streams, Whisper batches.

### TTS Flow
```
CAAL:     Text → Kokoro → Audio
Pipecat:  Text → Chatterbox → Audio
```
Chatterbox supports voice cloning.

### LLM (unchanged)
```
Both:     Text → Ollama → Text
```
Same Ollama setup, just different client library.
