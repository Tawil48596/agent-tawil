"""MCP 权限控制 — 工具白名单/黑名单"""

from typing import Optional


class MCPSecurity:
    """MCP 工具权限管理"""

    def __init__(self, config: dict = None):
        cfg = config or {}
        self._whitelist: set[str] = set(cfg.get("whitelist", []))
        self._blacklist: set[str] = set(cfg.get("blacklist", []))
        self._require_approval: set[str] = set(cfg.get("require_approval", []))

    def is_allowed(self, tool_name: str) -> bool:
        """检查工具是否可用"""
        if tool_name in self._blacklist:
            return False
        if self._whitelist and tool_name not in self._whitelist:
            return False
        return True

    def needs_approval(self, tool_name: str) -> bool:
        return tool_name in self._require_approval

    def add_whitelist(self, tool_name: str) -> None:
        self._whitelist.add(tool_name)

    def add_blacklist(self, tool_name: str) -> None:
        self._blacklist.add(tool_name)

    def get_config(self) -> dict:
        return {
            "whitelist": list(self._whitelist),
            "blacklist": list(self._blacklist),
            "require_approval": list(self._require_approval),
        }
