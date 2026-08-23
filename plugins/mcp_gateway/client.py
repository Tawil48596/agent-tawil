"""MCP Client — 连接外部 MCP Server"""

import json
from typing import Any

import structlog

logger = structlog.get_logger()


class MCPClient:
    """MCP 协议客户端

    连接到外部 MCP Server，发现工具并调用。
    """

    def __init__(self, endpoint: str):
        self._endpoint = endpoint
        self._connected = False
        self._tools: list[dict] = []
        self._server_info: dict[str, Any] = {}
        self._transport: Any | None = None  # stdio / sse / websocket

    async def connect(self) -> bool:
        """连接到 MCP Server"""
        try:
            # 尝试 stdio 模式 (子进程)
            if self._endpoint.startswith("stdio://"):
                return await self._connect_stdio()

            # 尝试 HTTP/SSE 模式
            elif self._endpoint.startswith("http"):
                return await self._connect_http()

            else:
                logger.warning("Unknown MCP endpoint scheme", endpoint=self._endpoint)
                return False

        except Exception as e:
            logger.error("MCP connection failed", endpoint=self._endpoint, error=str(e))
            return False

    async def _connect_stdio(self):
        """通过 stdio 连接 MCP Server (子进程)"""
        import asyncio

        cmd = self._endpoint.replace("stdio://", "")
        self._transport = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # 发送 initialize
        init_result = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
            },
        )
        self._server_info = init_result
        self._connected = True

        # 获取工具列表
        tools_result = await self._send_request("tools/list", {})
        self._tools = tools_result.get("tools", [])
        logger.info("MCP stdio connected", tools=len(self._tools))

        return True

    async def _connect_http(self):
        """通过 HTTP/SSE 连接 MCP Server"""
        import httpx

        self._transport = httpx.AsyncClient(base_url=self._endpoint, timeout=30.0)

        resp = await self._transport.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                },
                "id": 1,
            },
        )
        self._server_info = resp.json().get("result", {})
        self._connected = True

        resp = await self._transport.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2,
            },
        )
        self._tools = resp.json().get("result", {}).get("tools", [])
        logger.info("MCP HTTP connected", tools=len(self._tools))
        return True

    async def disconnect(self):
        if self._transport:
            if hasattr(self._transport, "terminate"):
                self._transport.terminate()
            elif hasattr(self._transport, "aclose"):
                await self._transport.aclose()
        self._connected = False

    # ── MCP 方法 ──

    async def list_tools(self) -> list[dict]:
        """列出 Server 提供的工具"""
        if not self._connected:
            await self.connect()
        return self._tools

    async def call_tool(self, name: str, arguments: dict) -> dict:
        """调用远程 MCP 工具"""
        return await self._send_request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments,
            },
        )

    async def _send_request(self, method: str, params: dict) -> dict:
        """发送 JSON-RPC 请求"""
        if self._transport is None:
            return {"error": "Not connected"}

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1,
        }

        # stdio 模式
        if hasattr(self._transport, "stdin"):
            self._transport.stdin.write((json.dumps(request) + "\n").encode())
            await self._transport.stdin.drain()
            line = await self._transport.stdout.readline()
            return json.loads(line.decode()).get("result", {})

        # HTTP 模式
        else:
            resp = await self._transport.post("/mcp", json=request)
            return resp.json().get("result", {})
