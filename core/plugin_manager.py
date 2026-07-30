"""插件管理器 — 发现、加载、生命周期管理、依赖解析"""

import importlib
import os
import sys
from pathlib import Path
from typing import Any

import structlog

from core.protocols import PluginProtocol

logger = structlog.get_logger()


class PluginManager:
    """负责插件的发现、加载、生命周期管理、依赖解析"""

    def __init__(self, plugin_dirs: list[str], event_bus=None, container=None):
        self._dirs = [Path(d) for d in plugin_dirs]
        self._plugins: dict[str, PluginProtocol] = {}
        self._load_order: list[str] = []
        self._extensions: dict[str, Any] = {}
        self._event_bus = event_bus
        self._container = container

    async def discover(self) -> list[str]:
        """扫描 plugin_dirs 下的所有 Python 包，自动发现插件"""
        discovered = []
        for d in self._dirs:
            if not d.exists():
                continue
            for item in d.iterdir():
                if item.is_dir() and not item.name.startswith("_") and not item.name.startswith("."):
                    plugin_file = item / "plugin.py"
                    if plugin_file.exists():
                        discovered.append(item.name)
                    elif (item / "__init__.py").exists():
                        discovered.append(item.name)
        logger.info("Plugins discovered", count=len(discovered), plugins=discovered)
        return discovered

    async def resolve_dependencies(self) -> list[str]:
        """拓扑排序依赖，检测循环依赖，返回加载顺序"""
        in_degree: dict[str, int] = {}
        graph: dict[str, list[str]] = {}

        for name, plugin in self._plugins.items():
            if name not in in_degree:
                in_degree[name] = 0
            for dep in plugin.dependencies:
                graph.setdefault(dep, []).append(name)
                in_degree[name] = in_degree.get(name, 0) + 1
                if dep not in in_degree:
                    in_degree[dep] = 0

        # Kahn's algorithm
        queue = [n for n, d in in_degree.items() if d == 0]
        order = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(in_degree):
            raise RuntimeError("Circular dependency detected in plugins")

        self._load_order = order
        return order

    async def load_all(self, container) -> None:
        """按依赖顺序加载所有插件"""
        for name in self._load_order:
            plugin = self._plugins.get(name)
            if plugin:
                await plugin.on_load(container)
                logger.info("Plugin loaded", name=name, version=plugin.version)

    async def enable_all(self) -> None:
        """按顺序启用所有插件"""
        for name in self._load_order:
            plugin = self._plugins.get(name)
            if plugin:
                await plugin.on_enable()
                exts = plugin.get_extensions()
                if exts:
                    self._extensions.update({f"{name}.{k}": v for k, v in exts.items()})
                logger.info("Plugin enabled", name=name)

    async def disable_all(self) -> None:
        """反向顺序禁用所有插件"""
        for name in reversed(self._load_order):
            plugin = self._plugins.get(name)
            if plugin:
                await plugin.on_disable()
                logger.info("Plugin disabled", name=name)

    def register(self, plugin: PluginProtocol) -> None:
        """手动注册插件"""
        self._plugins[plugin.name] = plugin

    def get_extension(self, name: str):
        """按名称获取扩展点接口"""
        return self._extensions.get(name)

    def get_plugin(self, name: str) -> PluginProtocol | None:
        return self._plugins.get(name)
