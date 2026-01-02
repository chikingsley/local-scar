"""MCP Server Configuration Loader.

Loads MCP server definitions from environment variables and optional JSON config file.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from mcp import ClientSession

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    name: str
    url: str
    auth_token: str | None = None
    transport: Literal["sse", "streamable_http"] | None = None
    timeout: float = 10.0


def load_mcp_config() -> list[MCPServerConfig]:
    """Load MCP server configurations from env vars and optional JSON file.

    n8n is loaded from environment variables (foundational).
    Additional MCP servers can be configured in mcp_servers.json.

    Environment variables:
        N8N_MCP_URL: n8n MCP server URL
        N8N_MCP_TOKEN: Bearer token for n8n (optional)
        N8N_MCP_TIMEOUT: Request timeout in seconds (optional, default 10.0)

    JSON file (mcp_servers.json):
        {
            "servers": [
                {
                    "name": "server_name",
                    "url": "http://...",
                    "token": "optional_token",
                    "transport": "sse" | "streamable_http",
                    "timeout": 10.0
                }
            ]
        }

    Returns:
        List of MCPServerConfig objects
    """
    servers = []

    # 1. n8n MCP Server from env (foundational)
    n8n_url = os.environ.get("N8N_MCP_URL")
    if n8n_url:
        servers.append(
            MCPServerConfig(
                name="n8n",
                url=n8n_url,
                auth_token=os.environ.get("N8N_MCP_TOKEN"),
                transport="streamable_http",
                timeout=float(os.environ.get("N8N_MCP_TIMEOUT", "10.0")),
            )
        )
        logger.debug(f"Loaded MCP server config: n8n ({n8n_url})")
    else:
        logger.info("N8N_MCP_URL not set - n8n MCP tools will not be available")

    # 2. Additional MCP servers from JSON config (optional)
    config_path = Path("mcp_servers.json")
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
                for server in data.get("servers", []):
                    name = server.get("name")
                    url = server.get("url")
                    if not name or not url:
                        logger.warning(f"Skipping MCP server with missing name or url: {server}")
                        continue

                    servers.append(
                        MCPServerConfig(
                            name=name,
                            url=url,
                            auth_token=server.get("token"),
                            transport=server.get("transport"),
                            timeout=server.get("timeout", 10.0),
                        )
                    )
                    logger.debug(f"Loaded MCP server config from JSON: {name} ({url})")
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
            if cfg.transport == "streamable_http" or cfg.url.endswith("/http"):
                read, write = await streamablehttp_client(cfg.url, headers=headers).__aenter__()
            else:
                read, write = await sse_client(cfg.url, headers=headers).__aenter__()

            session = ClientSession(read, write)
            await session.initialize()

            servers[cfg.name] = session
            logger.info(f"Initialized MCP server: {cfg.name}")

        except Exception as e:
            logger.error(f"Failed to initialize MCP server {cfg.name}: {e}", exc_info=True)

    return servers
