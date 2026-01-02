"""MCP Server Configuration Loader.

Loads MCP server definitions from environment variables and optional JSON config file.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

from ..config import get_settings

if TYPE_CHECKING:
    from mcp import ClientSession

logger = logging.getLogger(__name__)


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    name: str = Field(..., description="Server identifier")
    url: str = Field(..., description="Server URL")
    auth_token: str | None = Field(default=None, description="Bearer token for auth")
    transport: Literal["sse", "streamable_http"] | None = Field(
        default=None, description="Transport type"
    )
    timeout: float = Field(default=10.0, ge=1.0, description="Request timeout in seconds")


class MCPServersFile(BaseModel):
    """Schema for mcp_servers.json file."""

    servers: list[MCPServerConfig] = Field(default_factory=list)


def load_mcp_config() -> list[MCPServerConfig]:
    """Load MCP server configurations from settings and optional JSON file.

    n8n is loaded from settings/environment variables (foundational).
    Additional MCP servers can be configured in mcp_servers.json.

    Returns:
        List of MCPServerConfig objects
    """
    settings = get_settings()
    servers: list[MCPServerConfig] = []

    # 1. n8n MCP Server from settings (foundational)
    if settings.n8n_mcp_url:
        servers.append(
            MCPServerConfig(
                name="n8n",
                url=settings.n8n_mcp_url,
                auth_token=settings.n8n_mcp_token,
                transport="streamable_http",
                timeout=settings.n8n_mcp_timeout,
            )
        )
        logger.debug(f"Loaded MCP server config: n8n ({settings.n8n_mcp_url})")
    else:
        logger.info("N8N_MCP_URL not set - n8n MCP tools will not be available")

    # 2. Additional MCP servers from JSON config (optional)
    config_path = Path("mcp_servers.json")
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
                config_file = MCPServersFile.model_validate(data)
                servers.extend(config_file.servers)
                for server in config_file.servers:
                    logger.debug(f"Loaded MCP server config from JSON: {server.name} ({server.url})")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse mcp_servers.json: {e}")
        except Exception as e:
            logger.error(f"Failed to load mcp_servers.json: {e}")

    if not servers:
        logger.warning("No MCP servers configured - no MCP tools will be available")

    return servers


async def initialize_mcp_servers(
    configs: list[MCPServerConfig],
) -> dict[str, Any]:
    """Initialize MCP servers from config list.

    Args:
        configs: List of MCPServerConfig objects

    Returns:
        Dict mapping server name to initialized MCP client session
    """
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamablehttp_client

    servers: dict[str, ClientSession] = {}

    for cfg in configs:
        try:
            headers = {}
            if cfg.auth_token:
                headers["Authorization"] = f"Bearer {cfg.auth_token}"

            # Choose transport based on config
            # MCP client returns (read, write, get_session_id)
            if cfg.transport == "streamable_http" or cfg.url.endswith("/http"):
                read, write, _ = await streamablehttp_client(cfg.url, headers=headers).__aenter__()
            else:
                read, write, _ = await sse_client(cfg.url, headers=headers).__aenter__()

            session = ClientSession(read, write)
            await session.initialize()

            servers[cfg.name] = session
            logger.info(f"Initialized MCP server: {cfg.name}")

        except Exception as e:
            logger.error(f"Failed to initialize MCP server {cfg.name}: {e}", exc_info=True)

    return servers
