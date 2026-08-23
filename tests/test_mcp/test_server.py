"""Test MCP Server"""

import pytest

from plugins.mcp_gateway.server import MCPServer


@pytest.mark.asyncio
async def test_server_initialize():
    server = MCPServer()
    result = await server.handle_request("initialize")
    assert result["serverInfo"]["name"] == "ai-agent-platform"


@pytest.mark.asyncio
async def test_server_ping():
    server = MCPServer()
    result = await server.handle_request("ping")
    assert result == {}


@pytest.mark.asyncio
async def test_server_tool_call():
    server = MCPServer()
    server.register_tool(
        "echo",
        "Echo",
        {"properties": {"text": {"type": "string"}}, "required": ["text"]},
        lambda text: text,
    )
    result = await server.handle_request("tools/list")
    assert len(result["tools"]) == 1
    call_result = await server.handle_request(
        "tools/call", {"name": "echo", "arguments": {"text": "hello"}}
    )
    assert "hello" in call_result["content"][0]["text"]
