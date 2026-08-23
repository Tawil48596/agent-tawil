"""工具注册中心 — 完整的 Tool Schema + Handler 注册 + 热加载"""

from collections.abc import Callable
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger()


@dataclass
class ToolDef:
    """工具定义 — 完整的注册 Schema"""

    name: str
    description: str
    toolset: str = "custom"
    parameters: dict = field(default_factory=dict)
    handler: Callable | None = None
    check_fn: Callable | None = None
    requires_env: list[str] = field(default_factory=list)
    requires_packages: list[str] = field(default_factory=list)
    requires_system: list[str] = field(default_factory=list)
    version: str = "0.1.1"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    is_dangerous: bool = False
    installed: bool = True
    install_date: str = ""
    enabled: bool = True
    call_count: int = 0
    # Generative UI
    genui_component: str = ""  # 推荐的 UI 组件 (RepoCardGrid, CodeViewer...)
    genui_priority: int = 0  # 优先级

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "toolset": self.toolset,
            "parameters": self.parameters,
            "requires_env": self.requires_env,
            "requires_packages": self.requires_packages,
            "requires_system": self.requires_system,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "is_dangerous": self.is_dangerous,
            "installed": self.installed,
            "enabled": self.enabled,
            "genui_component": self.genui_component,
        }

    def to_openai_function(self) -> dict:
        """转为 OpenAI function-calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """工具注册中心"""

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}
        self._toolsets: dict[str, list[str]] = {}  # toolset → [tool_names]
        self._tags_index: dict[str, list[str]] = {}  # tag → [tool_names]

    # ── CRUD ──

    def register(self, tool: ToolDef):
        """注册工具"""
        self._tools[tool.name] = tool

        # 索引
        self._toolsets.setdefault(tool.toolset, []).append(tool.name)
        for tag in tool.tags:
            self._tags_index.setdefault(tag, []).append(tool.name)

        logger.info("Tool registered", name=tool.name, toolset=tool.toolset)

    def register_function(
        self, name: str, description: str, parameters: dict, handler: Callable, **kwargs
    ):
        """函数式注册 — 零代码侵入"""
        tool = ToolDef(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            **kwargs,
        )
        self.register(tool)
        return tool

    def unregister(self, name: str):
        tool = self._tools.pop(name, None)
        if tool:
            self._toolsets.get(tool.toolset, []).remove(name)
            for tag in tool.tags:
                self._tags_index.get(tag, []).remove(name)

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def list_all(self) -> list[ToolDef]:
        return list(self._tools.values())

    def list_installed(self) -> list[ToolDef]:
        return [t for t in self._tools.values() if t.installed]

    def list_enabled(self) -> list[ToolDef]:
        return [t for t in self._tools.values() if t.enabled]

    # ── 搜索 ──

    def search(
        self, query: str = "", toolset: str = "", tag: str = "", installed_only: bool = True
    ) -> list[ToolDef]:
        results = self.list_installed() if installed_only else self.list_all()

        if query:
            q = query.lower()
            results = [t for t in results if q in t.name.lower() or q in t.description.lower()]
        if toolset:
            results = [t for t in results if t.toolset == toolset]
        if tag:
            results = [t for t in results if tag in t.tags]

        return results

    # ── 统计 ──

    def get_stats(self) -> dict:
        return {
            "total": len(self._tools),
            "installed": len(self.list_installed()),
            "enabled": len(self.list_enabled()),
            "toolsets": {k: len(v) for k, v in self._toolsets.items()},
            "total_calls": sum(t.call_count for t in self._tools.values()),
        }

    # ── 依赖检查 ──

    def check_dependencies(self, tool: ToolDef) -> dict:
        """检查工具的依赖是否满足"""
        missing = {"env": [], "packages": [], "system": []}

        for env_var in tool.requires_env:
            import os

            if env_var not in os.environ:
                missing["env"].append(env_var)

        for pkg in tool.requires_packages:
            try:
                __import__(pkg.split(">=")[0].split("[")[0].strip())
            except ImportError:
                missing["packages"].append(pkg)

        for cmd in tool.requires_system:
            import shutil

            if not shutil.which(cmd):
                missing["system"].append(cmd)

        available = all(len(v) == 0 for v in missing.values())
        return {"available": available, "missing": missing}

    # ── 危险工具列表 ──

    def get_dangerous_tools(self) -> list[str]:
        return [t.name for t in self._tools.values() if t.is_dangerous]
