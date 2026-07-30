"""MCP 服务发现 — 自动检测可用 MCP Server"""

import json
import os
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class ServiceDiscovery:
    """MCP Server 自动发现

    扫描来源:
      1. 内置适配器 (plugins/mcp_gateway/adapters/)
      2. 配置文件 (mcp_servers.yaml / .mcp_config.json)
      3. 环境变量 (MCP_SERVER_*)
    """

    def __init__(self, config_paths: list[str] = None):
        self._config_paths = config_paths or [
            "mcp_servers.yaml",
            ".mcp_config.json",
            os.path.expanduser("~/.mcp_config.json"),
        ]

    async def scan(self) -> list[Any]:
        """扫描所有可用 MCP Server"""
        from plugins.mcp_gateway.gateway import MCPServerInfo
        servers = []

        # 1. 内置适配器
        servers.extend(self._discover_builtin())

        # 2. 配置文件
        servers.extend(self._discover_from_config())

        # 3. 环境变量
        servers.extend(self._discover_from_env())

        return servers

    def _discover_builtin(self) -> list[Any]:
        """发现内置适配器"""
        from plugins.mcp_gateway.gateway import MCPServerInfo
        servers = []

        adapters_dir = Path(__file__).parent / "adapters"
        if adapters_dir.exists():
            for py_file in adapters_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                module_name = py_file.stem
                label = module_name.replace("_", " ").title()
                servers.append(MCPServerInfo(
                    id=f"builtin:{module_name}",
                    name=f"{label} (内置)",
                    type=module_name,
                    endpoint=f"builtin://{module_name}",
                    status="discovered",
                    metadata={"auto_discovered": True},
                ))

        return servers

    def _discover_from_config(self) -> list[Any]:
        """从配置文件发现 MCP Server"""
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
                elif path.endswith(".yaml"):
                    import yaml
                    config = yaml.safe_load(content) or {}

                for server_entry in config.get("mcp_servers", []):
                    servers.append(MCPServerInfo(
                        id=server_entry.get("id", ""),
                        name=server_entry.get("name", ""),
                        type=server_entry.get("type", "custom"),
                        endpoint=server_entry.get("endpoint", ""),
                        metadata=server_entry.get("metadata", {}),
                    ))
            except Exception as e:
                logger.warning("Failed to parse MCP config", path=str(cfg_path), error=str(e))

        return servers

    def _discover_from_env(self) -> list[Any]:
        """从环境变量发现 MCP Server"""
        from plugins.mcp_gateway.gateway import MCPServerInfo
        servers = []

        for key, value in os.environ.items():
            if key.startswith("MCP_SERVER_"):
                name = key.replace("MCP_SERVER_", "").lower()
                servers.append(MCPServerInfo(
                    id=f"env:{name}",
                    name=name.replace("_", " ").title(),
                    type="custom",
                    endpoint=value,
                    metadata={"source": "environment"},
                ))

        return servers
