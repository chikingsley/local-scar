# Architecture Decisions

Migration from CAAL (LiveKit-based) to Pipecat-based local voice assistant.

## Core Stack Changes

| Component | CAAL (Before) | New (After) | Reason |
|-----------|---------------|-------------|--------|
| Framework | LiveKit Agents | Pipecat | More modular, better local support, no vendor lock-in |
| STT | Speaches (Faster-Whisper) | NVIDIA Riva (Parakeet) | 50x faster, 6% WER vs ~10%, true streaming |
| TTS | Kokoro | Chatterbox (Resemble AI) | SOTA quality, zero-shot voice cloning, emotion control, 23 languages |
| Transport | LiveKit Server | SmallWebRTCTransport | Self-contained, no external deps, p2p |
| Mobile | Flutter | React Native | Preference, better ecosystem |
| Type Checker | mypy | ty (Astral) | Faster, better DX |

## Keeping from CAAL

- n8n + MCP tool discovery (`src/caal/integrations/`)
- Webhook API design (`/announce`, `/wake`, `/reload-tools`, `/health`)
- Picovoice Porcupine wake word
- Tailscale networking (removing mkcert LAN HTTPS)
- n8n workflow examples
- Python backend with uv, ruff, pytest, hatchling

## Pipecat Utilities Needed

### Required
- **SileroVADAnalyzer** - Voice activity detection, MIT license, <1ms per chunk, best-in-class
- **LocalSmartTurnAnalyzerV3** - End-of-turn detection, runs locally via ONNX, <100ms inference
- **MCP integration** - Tool discovery from n8n workflows

### Transport
- **SmallWebRTCTransport** - Lightweight p2p WebRTC, self-hosted, no external services

### Audio
- NVIDIA Riva STT service (Parakeet model)
- Chatterbox TTS service

### Not Needed
- Daily/LiveKit transports (using SmallWebRTC)
- Fal Smart Turn (using local)
- Phone/IVR stuff
- Video/image generation
- Speech-to-speech

## STT Decision: Parakeet vs Canary

| Aspect | Parakeet | Canary |
|--------|----------|--------|
| Streaming | Yes | No (offline only) |
| Translation | No | Yes (25 languages) |
| Speed | 50x faster than Whisper | 10x faster than Whisper |
| Use Case | Real-time voice | Batch transcription + translation |

**Decision:** Parakeet - we need streaming for real-time voice, don't need translation.

## TTS Decision: Chatterbox

- MIT licensed, open source
- Zero-shot voice cloning (few seconds of audio)
- Emotion control parameter (monotone → expressive)
- Paralinguistic tags: `[laugh]`, `[cough]`, `[chuckle]`
- 23 languages
- 350M params (Turbo), low VRAM
- Outperforms ElevenLabs in blind tests (63.75% preference)
- Watermarking built-in (Perth)

Models:
- `chatterbox` - Original
- `chatterbox-turbo` - Faster, 1-step decoder
- `chatterbox-turbo-ONNX` - ONNX optimized

## Turn Detection: Local Smart Turn v3

Using LocalSmartTurnAnalyzerV3 (not Fal hosted):
- Runs on CPU via ONNX
- <100ms inference
- 23 languages
- No API costs

PyAnnote is for speaker diarization (who's speaking), not turn detection (when they're done). Different problem.

## Transport: SmallWebRTCTransport

- Direct p2p connection, no server infrastructure
- Self-contained, zero external dependencies
- Supported across: React, React Native, iOS, Android
- Good for: local deployment, demos, single-user
- Limitation: single client per bot (fine for our use case)

For multi-client/production scale: would need Daily or distributed WebRTC. Not our use case.

## Client SDKs

| Platform | Package |
|----------|---------|
| React | `@pipecat-ai/client-react` |
| React Native | `@pipecat-ai/client-react-native` + `small-webrtc-transport` |

RTVI is the underlying message format - handled automatically by the SDK.

## Removed from CAAL

- LiveKit server container
- Speaches container (Whisper STT)
- Kokoro container
- Flutter mobile app
- mkcert LAN HTTPS mode (Tailscale-only)
- nginx (SmallWebRTC doesn't need reverse proxy)

## Frontend

**Vite + React** (NOT Next.js)
- Fast dev server, simple build
- No SSR complexity needed for this use case

## Apple Silicon: FluidAudio

[FluidAudio](https://github.com/FluidInference/FluidAudio) solves the Mac problem:
- Swift SDK for Apple devices
- Runs Parakeet TDT v3 on Apple Neural Engine (ANE)
- Silero VAD included
- Speaker diarization (offline + streaming)
- Fully local, no cloud
- MIT/Apache 2.0 licensed

This replaces the mlx-audio workaround from CAAL. Same Parakeet model, native Apple optimization.

## Deployment Architecture

### What "Local" vs "Deployed" Means

**Docker containers** = isolated services that can run anywhere (your machine, a server, cloud)
**Native/Host** = runs directly on your OS, can access hardware (GPU, Neural Engine)

The key insight: some things MUST run native to access specialized hardware.

### NVIDIA GPU Setup (Linux/Windows)

Everything in Docker with CUDA access:

```
┌─────────────────────────────────────────────────────────┐
│  Docker Stack (NVIDIA GPU)                              │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Frontend   │  │  Chatterbox  │  │    Riva      │   │
│  │ (Vite+React) │  │    (TTS)     │  │  (Parakeet)  │   │
│  │    :3000     │  │    :5000     │  │    :50051    │   │
│  │              │  │   [CUDA]     │  │    [CUDA]    │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │           │
│         └─────────────────┼─────────────────┘           │
│                           │                             │
│                    ┌──────┴───────┐                     │
│                    │    Agent     │                     │
│                    │  (Pipecat)   │                     │
│                    │    :8889     │                     │
│                    └──────┬───────┘                     │
│                           │                             │
└───────────────────────────┼─────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
        ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
        │  Ollama   │ │    n8n    │ │   Your    │
        │   (LLM)   │ │ Workflows │ │   APIs    │
        │  [CUDA]   │ │           │ │           │
        └───────────┘ └───────────┘ └───────────┘
```

**Latency flow:**
1. Browser → WebRTC → Agent (local, ~1-5ms)
2. Agent → Riva STT (Docker, ~50-100ms for streaming chunk)
3. Agent → Ollama LLM (depends on model, ~200-500ms first token)
4. Agent → Chatterbox TTS (Docker, ~100-200ms first audio)
5. Agent → WebRTC → Browser (~1-5ms)

**Total round-trip:** ~400-800ms for first response audio (then streams)

### Apple Silicon Setup (Mac)

STT/TTS run NATIVE (to access Neural Engine), rest in Docker:

```
┌─────────────────────────────────────────────────────────┐
│  macOS Host                                             │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  FluidAudio (Native Swift)                      │    │
│  │  - Parakeet STT [ANE]                           │    │
│  │  - Silero VAD [ANE]                             │    │
│  │  - Kokoro TTS [ANE] (or Chatterbox via MPS)     │    │
│  │  :8000                                          │    │
│  └──────────────────────┬──────────────────────────┘    │
│                         │                               │
│  ┌──────────────────────┼──────────────────────────┐    │
│  │  Docker (ARM64)      │                          │    │
│  │                      │                          │    │
│  │  ┌──────────────┐    │    ┌──────────────┐      │    │
│  │  │   Frontend   │    │    │    Agent     │      │    │
│  │  │ (Vite+React) │◄───┼───►│  (Pipecat)   │      │    │
│  │  │    :3000     │    │    │    :8889     │      │    │
│  │  └──────────────┘    │    └──────┬───────┘      │    │
│  │                      │           │              │    │
│  └──────────────────────┼───────────┼──────────────┘    │
│                         │           │                   │
└─────────────────────────┼───────────┼───────────────────┘
                          │           │
                    ┌─────┴─────┐ ┌───┴───────┐
                    │  Ollama   │ │   n8n     │
                    │   [MPS]   │ │ Workflows │
                    └───────────┘ └───────────┘
```

**Why native for STT/TTS on Mac:**
- Docker on macOS cannot access Metal/MPS/ANE
- FluidAudio runs Parakeet on Neural Engine = fast + low power
- Ollama runs native with MPS (Metal) support

### Remote Access: Tailscale

Three options for accessing from outside your network:

| Method | Use Case | Public? |
|--------|----------|---------|
| Tailscale IP | Access from your devices on tailnet | No |
| `tailscale serve` | HTTPS proxy to local port, tailnet only | No |
| `tailscale funnel` | Expose to public internet | Yes |

**For personal use:** Tailscale IP or `tailscale serve` is enough
**For sharing:** `tailscale funnel` exposes to internet (free subdomain)

```bash
# Serve locally on tailnet (HTTPS)
tailscale serve https / http://localhost:3000

# Expose to public internet
tailscale funnel 443 http://localhost:3000
```

Caddy only needed if you want a custom domain. Tailscale handles certs automatically.

## Dev Tooling

| Tool | Status |
|------|--------|
| uv | Keep |
| ruff | Keep |
| pytest | Keep |
| hatchling | Keep |
| mypy | Replace with ty |

## Chatterbox Integration Path

Pipecat doesn't have native Chatterbox support yet ([issue #2549](https://github.com/pipecat-ai/pipecat/issues/2549)).

**Solution:** Use [Chatterbox-TTS-Server](https://github.com/devnen/Chatterbox-TTS-Server):
- FastAPI-based, OpenAI-compatible `/tts` endpoint
- Docker support with CUDA, ROCm, MPS, CPU
- Voice cloning via reference audio
- Supports both original and Turbo models
- Paralinguistic tags (`[laugh]`, `[cough]`)

Integration options:
1. Use Pipecat's OpenAI TTS service pointed at Chatterbox server
2. Build thin custom Pipecat TTS service wrapper

## Open Questions

1. **Riva deployment** - NIM container or NeMo toolkit directly?
2. **Voice cloning workflow** - How to handle reference audio upload for Chatterbox
3. **FluidAudio TTS** - FluidAudio includes Kokoro TTS, but we want Chatterbox. Options:
   - Run Chatterbox-TTS-Server with MPS on Mac
   - Use Kokoro from FluidAudio (simpler, but no voice cloning)
   - Hybrid: FluidAudio for STT, separate Chatterbox for TTS
