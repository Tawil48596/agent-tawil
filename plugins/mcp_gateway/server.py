"""MCP Server — 暴露 Agent 能力给外部 MCP Client"""

import json
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


class MCPServer:
    """MCP 协议服务端

    将 Agent 内部的工具以 MCP 协议暴露给外部 Client。
    参考: https://modelcontextprotocol.io/
    """

    def __init__(self, name: str = "ai-agent-platform", version: str = "0.1.0"):
        self.name = name
        self.version = version
        self._tools: dict[str, dict] = {}
        self._handlers: dict[str, Callable] = {}

    # ── 工具注册 ──

    def register_tool(self, name: str, description: str, parameters: dict, handler: Callable):
        """注册一个 MCP 工具"""
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": parameters.get("properties", {}),
                "required": parameters.get("required", []),
            },
        }
        self._handlers[name] = handler
        logger.debug("MCP tool registered", name=name)

    # ── MCP 协议方法 ──

    async def handle_request(self, method: str, params: dict = None) -> dict:
        """处理 MCP 协议请求"""
        params = params or {}

        if method == "tools/list":
            return {"tools": list(self._tools.values())}

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            return await self._call_tool(tool_name, arguments)

        elif method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": self.name, "version": self.version},
                "capabilities": {"tools": {}},
            }

        elif method == "ping":
            return {}

        else:
            return {"error": f"Unknown method: {method}"}

    async def _call_tool(self, name: str, arguments: dict) -> dict:
        """执行工具调用"""
        handler = self._handlers.get(name)
        if not handler:
            return {
                "content": [{"type": "text", "text": f"Tool not found: {name}"}],
                "isError": True,
            }

        try:
            import asyncio
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**arguments)
            else:
                result = handler(**arguments)

            if isinstance(result, str):
                text = result
            else:
                text = json.dumps(result, ensure_ascii=False, default=str)

            return {
                "content": [{"type": "text", "text": text}],
            }
        except Exception as e:
            logger.error("MCP tool error", name=name, error=str(e))
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True,
            }
