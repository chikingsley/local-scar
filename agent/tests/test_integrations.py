"""Tests for integrations module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from voice_agent.config import get_settings
from voice_agent.integrations.mcp import load_mcp_config
from voice_agent.integrations.n8n import (
    clear_caches,
    discover_n8n_workflows,
    extract_webhook_description,
    parse_mcp_result,
    sanitize_tool_name,
)


class TestMCPConfig:
    """Tests for MCP configuration loading."""

    def test_load_mcp_config_empty(self, monkeypatch):
        """Test loading config with no env vars."""
        monkeypatch.delenv("N8N_MCP_URL", raising=False)
        get_settings.cache_clear()

        configs = load_mcp_config()

        # Should return empty list when no config
        assert isinstance(configs, list)

    def test_load_mcp_config_with_n8n(self, monkeypatch):
        """Test loading config with n8n env var."""
        monkeypatch.setenv("N8N_MCP_URL", "http://localhost:5678/mcp-server/http")
        monkeypatch.setenv("N8N_MCP_TOKEN", "test-token")
        get_settings.cache_clear()

        configs = load_mcp_config()

        assert len(configs) == 1
        assert configs[0].name == "n8n"
        assert configs[0].url == "http://localhost:5678/mcp-server/http"
        assert configs[0].auth_token == "test-token"


class TestN8nIntegration:
    """Tests for n8n workflow integration."""

    def test_sanitize_tool_name(self):
        """Test tool name sanitization."""
        assert sanitize_tool_name("My Workflow") == "my_workflow"
        assert sanitize_tool_name("get-data") == "get_data"
        assert sanitize_tool_name("UPPER_CASE") == "upper_case"

    def test_extract_webhook_description(self, sample_workflow_details):
        """Test extracting description from webhook node."""
        description = extract_webhook_description(sample_workflow_details)
        assert "This workflow does something useful" in description

    def test_extract_webhook_description_no_notes(self):
        """Test extraction with no notes field."""
        workflow = {"workflow": {"nodes": [{"type": "n8n-nodes-base.webhook"}]}}
        description = extract_webhook_description(workflow)
        assert description == ""

    def test_clear_caches(self):
        """Test cache clearing."""
        # Should not raise
        clear_caches()

    def test_parse_mcp_result_json(self):
        """Test parsing JSON MCP result."""
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text='{"key": "value"}')]

        result = parse_mcp_result(mock_result)
        assert result == {"key": "value"}

    def test_parse_mcp_result_plain_text(self):
        """Test parsing plain text MCP result."""
        mock_result = MagicMock()
        mock_result.content = [MagicMock(text="plain text")]

        result = parse_mcp_result(mock_result)
        assert result == "plain text"

    @pytest.mark.asyncio
    async def test_discover_n8n_workflows(self, mock_mcp_client, sample_workflows):
        """Test workflow discovery."""
        # Mock the MCP client responses
        mock_mcp_client.call_tool = AsyncMock(
            side_effect=[
                MagicMock(content=[MagicMock(text=str(sample_workflows).replace("'", '"'))]),
            ]
        )

        tools, name_map = await discover_n8n_workflows(
            mock_mcp_client, "http://localhost:5678"
        )

        assert isinstance(tools, list)
        assert isinstance(name_map, dict)


class TestWebSearch:
    """Tests for web search integration."""

    def test_web_search_tool_import(self):
        """Test that WebSearchTool can be imported."""
        from voice_agent.integrations.web_search import WebSearchTool

        tool = WebSearchTool(max_results=3, timeout=5.0)
        assert tool.max_results == 3
        assert tool.timeout == 5.0
