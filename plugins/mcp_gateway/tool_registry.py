"""MCP 工具注册表 — 管理所有已发现 MCP 工具"""

from typing import Any

import structlog

logger = structlog.get_logger()


class MCPToolRegistry:
    """MCP 工具注册中心"""

    def __init__(self):
        self._tools: dict[str, dict[str, Any]] = {}  # tool_name → {definition, source}

    def register(self, tool_def: dict, source: str = ""):
        """注册工具"""
        name = tool_def.get("name", "")
        if not name:
            return
        self._tools[name] = {
            "definition": tool_def,
            "source": source,
        }

    def unregister(self, name: str):
        self._tools.pop(name, None)

    def unregister_source(self, source: str):
        """移除某个 MCP Server 的所有工具"""
        to_remove = [n for n, t in self._tools.items() if t["source"] == source]
        for name in to_remove:
            del self._tools[name]
        logger.info("MCP tools unregistered", source=source, count=len(to_remove))

    def get(self, name: str) -> dict | None:
        return self._tools.get(name)

    def list_all(self) -> list[dict]:
        """列出所有工具"""
        return [
            {
                "name": name,
                "description": info["definition"].get("description", ""),
                "source": info["source"],
                "parameters": info["definition"].get("inputSchema", {}),
            }
            for name, info in self._tools.items()
        ]

    def list_for_llm(self) -> list[dict]:
        """转换为 OpenAI function-calling 格式"""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": info["definition"].get("description", ""),
                    "parameters": info["definition"].get(
                        "inputSchema",
                        {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    ),
                },
            }
            for name, info in self._tools.items()
        ]
