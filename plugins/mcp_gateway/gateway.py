"""MCP gateway lifecycle, validation, timeout and approval boundary."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from plugins.mcp_gateway.client import MCPClient
from plugins.mcp_gateway.discovery import ServiceDiscovery
from plugins.mcp_gateway.security import MCPSecurity
from plugins.mcp_gateway.tool_registry import MCPToolRegistry

logger = structlog.get_logger()


@dataclass
class MCPServerInfo:
    id: str
    name: str
    type: str
    endpoint: str
    status: str = "disconnected"
    tools_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class MCPGateway:
    def __init__(self, config: dict[str, Any] = None):
        cfg = config or {}
        mcp_cfg = cfg.get("mcp", {}) if isinstance(cfg, dict) else {}
        self._servers: dict[str, MCPServerInfo] = {}
        self._clients: dict[str, MCPClient] = {}
        self._server_instances: dict[str, Any] = {}
        self._tool_registry = MCPToolRegistry()
        self._discovery = ServiceDiscovery()
        self._tool_call_timeout = mcp_cfg.get("tool_call_timeout", 30)
        security_cfg = dict(mcp_cfg.get("security", {}))
        security_cfg.setdefault("require_approval", ["github_clone_repo"])
        self._security = MCPSecurity(security_cfg)

    async def register_server(self, info: MCPServerInfo, adapter: Any = None) -> str:
        self._servers[info.id] = info
        if adapter:
            self._server_instances[info.id] = adapter
            info.status = "connected"
            tools = adapter.list_tools() if hasattr(adapter, "list_tools") else []
            info.tools_count = len(tools)
            for tool in tools:
                self._tool_registry.register(tool, source=info.id)
        else:
            client = MCPClient(info.endpoint)
            self._clients[info.id] = client
            try:
                await client.connect()
                info.status = "connected"
                tools = await client.list_tools()
                info.tools_count = len(tools)
                for tool in tools:
                    self._tool_registry.register(tool, source=info.id)
            except Exception as exc:
                info.status = "error"
                logger.error("MCP server connection failed", id=info.id, error=str(exc))
        return info.id

    async def unregister_server(self, server_id: str) -> None:
        if server_id in self._clients:
            await self._clients[server_id].disconnect()
            del self._clients[server_id]
        self._server_instances.pop(server_id, None)
        self._servers.pop(server_id, None)
        self._tool_registry.unregister_source(server_id)

    def get_server(self, server_id: str) -> Optional[MCPServerInfo]:
        return self._servers.get(server_id)

    def list_servers(self) -> list[MCPServerInfo]:
        return list(self._servers.values())

    @staticmethod
    def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
        return {"ok": False, "error": {"code": code, "message": message}, **extra}

    @staticmethod
    def _validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> Optional[str]:
        if not isinstance(arguments, dict):
            return "arguments must be an object"
        for name in schema.get("required", []):
            if name not in arguments:
                return f"missing required argument: {name}"
        expected = {"string": str, "integer": int, "number": (int, float),
                    "boolean": bool, "object": dict, "array": list}
        for name, value in arguments.items():
            spec = schema.get("properties", {}).get(name, {})
            py_type = expected.get(spec.get("type"))
            if py_type and (not isinstance(value, py_type) or
                            spec.get("type") == "integer" and isinstance(value, bool)):
                return f"argument {name} must be {spec['type']}"
            if "enum" in spec and value not in spec["enum"]:
                return f"argument {name} must be one of {spec['enum']}"
        return None

    async def call_tool(self, tool_name: str, arguments: dict[str, Any],
                        approved: bool = False) -> dict[str, Any]:
        tool_info = self._tool_registry.get(tool_name)
        if not tool_info:
            return self._error("tool_not_found", f"Tool not found: {tool_name}")
        if not self._security.is_allowed(tool_name):
            return self._error("tool_forbidden", f"Tool is not allowed: {tool_name}")
        if self._security.needs_approval(tool_name) and not approved:
            return self._error("approval_required", "Explicit approval is required",
                               approval_required=True, tool=tool_name)
        validation_error = self._validate_arguments(
            tool_info["definition"].get("inputSchema", {}), arguments)
        if validation_error:
            return self._error("invalid_arguments", validation_error)

        server_id = tool_info.get("source", "")
        adapter = self._server_instances.get(server_id)
        client = self._clients.get(server_id)
        if not adapter and not client:
            return self._error("server_disconnected", f"Server not connected: {server_id}")
        started = time.monotonic()
        try:
            call = (adapter.call_tool(tool_name, arguments) if adapter
                    else client.call_tool(tool_name, arguments))
            result = await asyncio.wait_for(call, timeout=self._tool_call_timeout)
        except asyncio.TimeoutError:
            return self._error("tool_timeout", f"Tool exceeded {self._tool_call_timeout}s timeout")
        except Exception as exc:
            logger.exception("MCP tool call failed", tool=tool_name, server=server_id)
            return self._error("tool_call_failed", str(exc))
        meta = {"tool": tool_name, "server": server_id,
                "duration_ms": round((time.monotonic() - started) * 1000, 2)}
        if isinstance(result, dict):
            result.setdefault("_meta", meta)
            return result
        return {"result": result, "_meta": meta}

    async def refresh_server(self, server_id: str) -> MCPServerInfo:
        info = self._servers.get(server_id)
        if not info:
            raise ValueError(f"Server not found: {server_id}")
        self._tool_registry.unregister_source(server_id)
        try:
            adapter = self._server_instances.get(server_id)
            if adapter:
                tools = adapter.list_tools()
            else:
                client = self._clients[server_id]
                await client.connect()
                tools = await client.list_tools()
            for tool in tools:
                self._tool_registry.register(tool, source=server_id)
            info.tools_count = len(tools)
            info.status = "connected"
        except Exception:
            info.status = "error"
            info.tools_count = 0
            raise
        return info

    def health(self) -> dict[str, Any]:
        servers = self.list_servers()
        return {"status": "ok" if all(s.status == "connected" for s in servers) else "degraded",
                "servers": [{"id": s.id, "status": s.status, "tools_count": s.tools_count}
                            for s in servers]}

    def list_all_tools(self) -> list[dict]:
        return self._tool_registry.list_all()

    async def discover(self) -> None:
        for server_info in await self._discovery.scan():
            if server_info.id not in self._servers:
                await self.register_server(server_info)
