"""MCP 服务发现 — 自动检测可用 MCP Server"""

import json
import os
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class ServiceDiscovery:
    """MCP Server 自动发现"""

    def __init__(self, config_paths: list[str] = None):
        self._config_paths = config_paths or [
            "mcp_servers.yaml",
            ".mcp_config.json",
            os.path.expanduser("~/.mcp_config.json"),
        ]

    async def scan(self) -> list[Any]:
        from plugins.mcp_gateway.gateway import MCPServerInfo
        servers = []
        servers.extend(self._discover_from_config())
        servers.extend(self._discover_from_env())
        return servers

    def _discover_from_config(self) -> list[Any]:
        from plugins.mcp_gateway.gateway import MCPServerInfo
        servers = []
        for path in self._config_paths:
            cfg_path = Path(path)
            if not cfg_path.exists():
                continue
            try:
                content = cfg_path.read_text(encoding="utf-8")
                config = {}
                if path.endswith(".json"):
                    config = json.loads(content)
                elif path.endswith((".yaml", ".yml")):
                    import yaml
                    config = yaml.safe_load(content) or {}
                for entry in config.get("mcp_servers", []):
                    servers.append(MCPServerInfo(
                        id=entry.get("id", ""), name=entry.get("name", ""),
                        type=entry.get("type", "custom"),
                        endpoint=entry.get("endpoint", ""),
                        metadata=entry.get("metadata", {}),
                    ))
            except Exception as e:
                logger.debug("Failed to parse MCP config", path=str(cfg_path), error=str(e))
        return servers

    def _discover_from_env(self) -> list[Any]:
        from plugins.mcp_gateway.gateway import MCPServerInfo
        servers = []
        for key, value in os.environ.items():
            if key.startswith("MCP_SERVER_"):
                name = key.replace("MCP_SERVER_", "").lower()
                servers.append(MCPServerInfo(
                    id=f"env:{name}", name=name.replace("_", " ").title(),
                    type="custom", endpoint=value,
                    metadata={"source": "environment"},
                ))
        return servers
