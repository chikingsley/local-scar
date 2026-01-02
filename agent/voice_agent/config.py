"""Configuration management using Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables.

    All settings can be overridden via environment variables.
    Supports .env file loading.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # STT (NVIDIA Parakeet via NVCF)
    nvidia_api_key: str = Field(
        default="",
        description="NVIDIA API key for STT (get from build.nvidia.com)",
    )
    nvidia_server: str = Field(
        default="grpc.nvcf.nvidia.com:443",
        description="NVIDIA STT gRPC server URL",
    )

    # TTS (Chatterbox)
    chatterbox_url: Annotated[str, HttpUrl] = Field(
        default="http://localhost:5000",
        description="Chatterbox TTS server URL",
    )
    tts_voice: str = Field(
        default="default",
        description="TTS voice name or reference audio path",
    )
    tts_exaggeration: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Emotion intensity (0=monotone, 1=expressive)",
    )

    # LLM (Ollama)
    ollama_host: Annotated[str, HttpUrl] = Field(
        default="http://localhost:11434",
        description="Ollama API server URL",
    )
    ollama_model: str = Field(
        default="qwen3:8b",
        description="Ollama model name",
    )
    ollama_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature",
    )
    ollama_num_ctx: int = Field(
        default=8192,
        ge=1024,
        description="LLM context window size",
    )

    # n8n MCP (optional)
    n8n_mcp_url: str | None = Field(
        default=None,
        description="n8n MCP server URL",
    )
    n8n_mcp_token: str | None = Field(
        default=None,
        description="n8n MCP authentication token",
    )
    n8n_mcp_timeout: float = Field(
        default=10.0,
        ge=1.0,
        description="n8n MCP request timeout in seconds",
    )

    # Server ports
    webhook_port: int = Field(
        default=8889,
        ge=1,
        le=65535,
        description="Webhook API server port",
    )
    webrtc_port: int = Field(
        default=8765,
        ge=1,
        le=65535,
        description="WebRTC signaling server port",
    )

    # Paths
    prompts_dir: Path = Field(
        default=Path("prompts"),
        description="Directory containing prompt templates",
    )

    @field_validator("prompts_dir", mode="before")
    @classmethod
    def resolve_prompts_dir(cls, v: str | Path) -> Path:
        """Resolve prompts directory path."""
        path = Path(v)
        if not path.is_absolute():
            # Relative to project root
            path = Path(__file__).parent.parent / path
        return path


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Use this function to access settings throughout the application.
    Settings are loaded once and cached for performance.
    """
    return Settings()


# Convenience alias
settings = get_settings()
