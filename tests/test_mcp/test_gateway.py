import asyncio

import pytest

from plugins.mcp_gateway.gateway import MCPGateway, MCPServerInfo


class FakeAdapter:
    def __init__(self, delay=0):
        self.delay = delay

    def list_tools(self):
        return [{"name": "echo", "inputSchema": {"type": "object",
                 "properties": {"text": {"type": "string"}}, "required": ["text"]}},
                {"name": "github_clone_repo", "inputSchema": {"type": "object",
                 "properties": {"owner": {"type": "string"}}, "required": ["owner"]}}]

    async def call_tool(self, name, arguments):
        await asyncio.sleep(self.delay)
        return {"value": arguments}


@pytest.mark.asyncio
async def test_gateway_validates_and_adds_metadata():
    gateway = MCPGateway()
    await gateway.register_server(MCPServerInfo("test", "Test", "custom", ""), FakeAdapter())
    invalid = await gateway.call_tool("echo", {})
    assert invalid["error"]["code"] == "invalid_arguments"
    result = await gateway.call_tool("echo", {"text": "hello"})
    assert result["value"]["text"] == "hello"
    assert result["_meta"]["server"] == "test"


@pytest.mark.asyncio
async def test_gateway_requires_approval_and_refreshes():
    gateway = MCPGateway()
    await gateway.register_server(MCPServerInfo("test", "Test", "custom", ""), FakeAdapter())
    denied = await gateway.call_tool("github_clone_repo", {"owner": "openai"})
    assert denied["approval_required"] is True
    allowed = await gateway.call_tool("github_clone_repo", {"owner": "openai"}, approved=True)
    assert "value" in allowed
    info = await gateway.refresh_server("test")
    assert info.tools_count == 2


@pytest.mark.asyncio
async def test_gateway_enforces_timeout():
    gateway = MCPGateway({"mcp": {"tool_call_timeout": 0.01}})
    await gateway.register_server(MCPServerInfo("test", "Test", "custom", ""), FakeAdapter(0.1))
    result = await gateway.call_tool("echo", {"text": "slow"})
    assert result["error"]["code"] == "tool_timeout"
