"""MCP 网关 — 统一入口，管理所有 MCP Server 连接"""

from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from plugins.mcp_gateway.client import MCPClient
from plugins.mcp_gateway.server import MCPServer
from plugins.mcp_gateway.discovery import ServiceDiscovery
from plugins.mcp_gateway.tool_registry import MCPToolRegistry

logger = structlog.get_logger()


@dataclass
class MCPServerInfo:
    id: str
    name: str
    type: str               # github | filesystem | database | custom
    endpoint: str           # 连接字符串或 URL
    status: str = "disconnected"  # connected | disconnected | error
    tools_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class MCPGateway:
    """MCP 网关 — 统一管理所有 MCP 连接和工具发现"""

    def __init__(self, config: dict[str, Any] = None):
        cfg = config or {}
        mcp_cfg = cfg.get("mcp", {}) if isinstance(cfg, dict) else {}

        self._servers: dict[str, MCPServerInfo] = {}
        self._clients: dict[str, MCPClient] = {}
        self._server_instances: dict[str, Any] = {}  # 运行中的 MCPServer 实例
        self._tool_registry = MCPToolRegistry()
        self._discovery = ServiceDiscovery()
        self._tool_call_timeout = mcp_cfg.get("tool_call_timeout", 30)

    # ── Server 管理 ──

    async def register_server(self, info: MCPServerInfo, adapter: Any = None) -> str:
        """注册 MCP Server 并连接"""
        self._servers[info.id] = info

        if adapter:
            self._server_instances[info.id] = adapter
            info.status = "connected"
            tools = adapter.list_tools() if hasattr(adapter, "list_tools") else []
            info.tools_count = len(tools)
            for tool in tools:
                self._tool_registry.register(tool, source=info.id)
            logger.info("MCP server registered", id=info.id, name=info.name, tools=len(tools))
        else:
            # 外部 MCP Server — 通过 Client 连接
            client = MCPClient(info.endpoint)
            self._clients[info.id] = client
            try:
                await client.connect()
                info.status = "connected"
                tools = await client.list_tools()
                info.tools_count = len(tools)
                for tool in tools:
                    self._tool_registry.register(tool, source=info.id)
                logger.info("MCP server connected", id=info.id, name=info.name, tools=len(tools))
            except Exception as e:
                info.status = "error"
                logger.error("MCP server connection failed", id=info.id, error=str(e))

        return info.id

    async def unregister_server(self, server_id: str):
        """移除 MCP Server"""
        if server_id in self._clients:
            await self._clients[server_id].disconnect()
            del self._clients[server_id]
        self._server_instances.pop(server_id, None)
        self._servers.pop(server_id, None)
        self._tool_registry.unregister_source(server_id)
        logger.info("MCP server unregistered", id=server_id)

    def get_server(self, server_id: str) -> Optional[MCPServerInfo]:
        return self._servers.get(server_id)

    def list_servers(self) -> list[MCPServerInfo]:
        return list(self._servers.values())

    # ── 工具调用 ──

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """调用 MCP 工具"""
        tool_info = self._tool_registry.get(tool_name)
        if not tool_info:
            return {"error": f"Tool not found: {tool_name}"}

        server_id = tool_info.get("source", "")
        adapter = self._server_instances.get(server_id)

        if adapter:
            # 本地适配器 — 直接调用
            return await adapter.call_tool(tool_name, arguments)
        else:
            # 外部 MCP Server — 通过 Client
            client = self._clients.get(server_id)
            if not client:
                return {"error": f"Server not connected: {server_id}"}
            return await client.call_tool(tool_name, arguments)

    # ── 工具发现 ──

    def list_all_tools(self) -> list[dict]:
        """列出所有已注册的 MCP 工具"""
        return self._tool_registry.list_all()

    async def discover(self):
        """自动发现可用 MCP Server"""
        discovered = await self._discovery.scan()
        for server_info in discovered:
            if server_info.id not in self._servers:
                await self.register_server(server_info)
