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

## Docker Services

```
┌─────────────────────────────────────────────────────────┐
│  Docker Stack                                           │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Frontend   │  │  Chatterbox  │  │    Riva      │   │
│  │   (Next.js)  │  │    (TTS)     │  │  (Parakeet)  │   │
│  │    :3000     │  │    :5000     │  │    :50051    │   │
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
        └───────────┘ └───────────┘ └───────────┘
```

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
2. **Apple Silicon** - Riva doesn't support Metal, may need alternative for Mac (keep mlx-audio option?)
3. **Voice cloning workflow** - How to handle reference audio upload for Chatterbox
