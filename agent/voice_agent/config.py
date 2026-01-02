"""Configuration management."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")


@dataclass
class Config:
    """Application configuration from environment."""

    # STT (Riva/Parakeet)
    riva_url: str = field(default_factory=lambda: os.getenv("RIVA_URL", "localhost:50051"))
    riva_model: str = field(default_factory=lambda: os.getenv("RIVA_MODEL", "parakeet-tdt-0.6b"))

    # TTS (Chatterbox)
    chatterbox_url: str = field(
        default_factory=lambda: os.getenv("CHATTERBOX_URL", "http://localhost:5000")
    )
    tts_voice: str = field(default_factory=lambda: os.getenv("TTS_VOICE", "default"))

    # LLM (Ollama)
    ollama_host: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434")
    )
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen3:8b"))
    ollama_temperature: float = field(
        default_factory=lambda: float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
    )
    ollama_num_ctx: int = field(
        default_factory=lambda: int(os.getenv("OLLAMA_NUM_CTX", "8192"))
    )

    # n8n MCP
    n8n_mcp_url: str | None = field(default_factory=lambda: os.getenv("N8N_MCP_URL"))
    n8n_mcp_token: str | None = field(default_factory=lambda: os.getenv("N8N_MCP_TOKEN"))

    # Webhook server
    webhook_port: int = field(default_factory=lambda: int(os.getenv("WEBHOOK_PORT", "8889")))

    # WebRTC
    webrtc_port: int = field(default_factory=lambda: int(os.getenv("WEBRTC_PORT", "8765")))

    # Paths
    prompts_dir: Path = field(
        default_factory=lambda: Path(os.getenv("PROMPTS_DIR", str(_project_root / "prompts")))
    )

    @classmethod
    def load(cls) -> Config:
        """Load configuration from environment."""
        return cls()


# Global config instance
config = Config.load()
