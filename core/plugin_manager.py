"""Runtime plugin discovery, dependency ordering and lifecycle isolation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from core.protocols import PluginProtocol

logger = structlog.get_logger()


@dataclass
class PluginState:
    status: str = "registered"
    error: str = ""


class PluginManager:
    def __init__(self, plugin_dirs: list[str], event_bus=None, container=None):
        self._dirs = [Path(path) for path in plugin_dirs]
        self._plugins: dict[str, PluginProtocol] = {}
        self._states: dict[str, PluginState] = {}
        self._load_order: list[str] = []
        self._extensions: dict[str, Any] = {}
        self._event_bus = event_bus
        self._container = container

    async def discover(self) -> list[str]:
        discovered = []
        for directory in self._dirs:
            if not directory.exists():
                continue
            for item in directory.iterdir():
                if (item.is_dir() and not item.name.startswith(("_", ".")) and
                        ((item / "plugin.py").exists() or (item / "__init__.py").exists())):
                    discovered.append(item.name)
        return sorted(set(discovered))

    def register(self, plugin: PluginProtocol) -> None:
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin already registered: {plugin.name}")
        self._plugins[plugin.name] = plugin
        self._states[plugin.name] = PluginState()

    async def resolve_dependencies(self) -> list[str]:
        names = set(self._plugins)
        missing = {name: [dep for dep in plugin.dependencies if dep not in names]
                   for name, plugin in self._plugins.items()}
        missing = {name: deps for name, deps in missing.items() if deps}
        if missing:
            details = ", ".join(f"{name}: {deps}" for name, deps in missing.items())
            raise RuntimeError(f"Missing plugin dependencies: {details}")
        in_degree = {name: 0 for name in names}
        graph = {name: [] for name in names}
        for name, plugin in self._plugins.items():
            for dependency in plugin.dependencies:
                graph[dependency].append(name)
                in_degree[name] += 1
        queue = sorted(name for name, degree in in_degree.items() if degree == 0)
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    queue.sort()
        if len(order) != len(names):
            raise RuntimeError("Circular dependency detected in plugins")
        self._load_order = order
        return order

    async def load_all(self, container=None) -> None:
        container = container or self._container
        if not self._load_order:
            await self.resolve_dependencies()
        for name in self._load_order:
            plugin = self._plugins[name]
            try:
                await plugin.on_load(container)
                self._states[name] = PluginState("loaded")
            except Exception as exc:
                self._states[name] = PluginState("error", str(exc))
                logger.exception("Plugin load failed", name=name)
                raise RuntimeError(f"Plugin load failed: {name}: {exc}") from exc

    async def enable(self, name: str) -> None:
        plugin = self._plugins.get(name)
        if not plugin:
            raise KeyError(f"Plugin not found: {name}")
        if self._states[name].status not in ("loaded", "disabled"):
            raise RuntimeError(f"Plugin is not loadable from state: {self._states[name].status}")
        try:
            await plugin.on_enable()
            for key, value in plugin.get_extensions().items():
                self._extensions[f"{name}.{key}"] = value
            self._states[name] = PluginState("enabled")
        except Exception as exc:
            self._states[name] = PluginState("error", str(exc))
            raise

    async def enable_all(self) -> None:
        for name in self._load_order:
            await self.enable(name)

    async def disable(self, name: str) -> None:
        plugin = self._plugins.get(name)
        if not plugin:
            raise KeyError(f"Plugin not found: {name}")
        await plugin.on_disable()
        prefix = f"{name}."
        self._extensions = {key: value for key, value in self._extensions.items()
                            if not key.startswith(prefix)}
        self._states[name] = PluginState("disabled")

    async def disable_all(self) -> None:
        for name in reversed(self._load_order):
            if self._states[name].status == "enabled":
                try:
                    await self.disable(name)
                except Exception as exc:
                    self._states[name] = PluginState("error", str(exc))
                    logger.exception("Plugin shutdown failed", name=name)

    def get_extension(self, name: str):
        return self._extensions.get(name)

    def get_plugin(self, name: str) -> PluginProtocol | None:
        return self._plugins.get(name)

    def health(self) -> dict:
        return {name: {"version": self._plugins[name].version, "status": state.status,
                       "error": state.error, "dependencies": self._plugins[name].dependencies}
                for name, state in self._states.items()}
