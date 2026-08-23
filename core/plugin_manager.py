"""Runtime plugin discovery, dependency ordering and lifecycle isolation."""

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog

from core.di_container import DIContainer
from core.protocols import PluginProtocol

logger = structlog.get_logger()


@dataclass
class PluginState:
    status: str = "registered"
    error: str = ""


class PluginManager:
    def __init__(
        self,
        plugin_dirs: list[str],
        event_bus: Any | None = None,
        container: DIContainer | None = None,
    ) -> None:
        self._dirs = [Path(path) for path in plugin_dirs]
        self._plugins: dict[str, PluginProtocol] = {}
        self._states: dict[str, PluginState] = {}
        self._load_order: list[str] = []
        self._extensions: dict[str, Any] = {}
        self._discovery_errors: dict[str, str] = {}
        self._event_bus = event_bus
        self._container = container

    def _plugin_files(self) -> list[Path]:
        files: list[Path] = []
        for directory in self._dirs:
            if not directory.exists():
                continue
            files.extend(
                item / "plugin.py"
                for item in directory.iterdir()
                if item.is_dir()
                and not item.name.startswith(("_", "."))
                and (item / "plugin.py").exists()
            )
        return sorted(set(files), key=lambda path: str(path))

    async def discover(self) -> list[str]:
        return [path.parent.name for path in self._plugin_files()]

    async def discover_and_register(self) -> list[str]:
        """Import explicit ``create_plugin`` entrypoints and register their plugins."""
        registered: list[str] = []
        for path in self._plugin_files():
            entrypoint_name = path.parent.name
            try:
                module_name = f"agent_plugin_{entrypoint_name}_{abs(hash(path))}"
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    raise RuntimeError(f"Cannot import plugin entrypoint: {path}")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                factory = getattr(module, "create_plugin", None)
                if not callable(factory):
                    raise TypeError(f"Plugin entrypoint has no create_plugin() factory: {path}")
                plugin = factory()
                if not isinstance(plugin, PluginProtocol):
                    raise TypeError(f"Plugin entrypoint returned an invalid plugin: {path}")
                self.register(plugin)
            except Exception as exc:
                self._discovery_errors[entrypoint_name] = str(exc)
                logger.exception("Plugin discovery failed", name=entrypoint_name, path=str(path))
                continue
            self._discovery_errors.pop(entrypoint_name, None)
            registered.append(plugin.name)
        return registered

    def register(self, plugin: PluginProtocol) -> None:
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin already registered: {plugin.name}")
        self._plugins[plugin.name] = plugin
        self._states[plugin.name] = PluginState()

    async def resolve_dependencies(self) -> list[str]:
        names = set(self._plugins)
        missing = {
            name: [dep for dep in plugin.dependencies if dep not in names]
            for name, plugin in self._plugins.items()
        }
        missing = {name: deps for name, deps in missing.items() if deps}
        if missing:
            details = ", ".join(f"{name}: {deps}" for name, deps in missing.items())
            raise RuntimeError(f"Missing plugin dependencies: {details}")
        in_degree = dict.fromkeys(names, 0)
        graph: dict[str, list[str]] = {name: [] for name in names}
        for name, plugin in self._plugins.items():
            for dependency in plugin.dependencies:
                graph[dependency].append(name)
                in_degree[name] += 1
        queue = sorted(name for name, degree in in_degree.items() if degree == 0)
        order: list[str] = []
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

    async def load_all(self, container: DIContainer | None = None) -> None:
        container = container or self._container
        if not self._load_order:
            await self.resolve_dependencies()
        for name in self._load_order:
            plugin = self._plugins[name]
            unavailable = [
                dependency
                for dependency in plugin.dependencies
                if self._states[dependency].status != "loaded"
            ]
            if unavailable:
                self._states[name] = PluginState(
                    "blocked", f"Unavailable dependencies: {', '.join(unavailable)}"
                )
                continue
            try:
                await plugin.on_load(container)
                self._states[name] = PluginState("loaded")
            except Exception as exc:
                self._states[name] = PluginState("error", str(exc))
                logger.exception("Plugin load failed", name=name)

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
            if self._states[name].status != "loaded":
                continue
            unavailable = [
                dependency
                for dependency in self._plugins[name].dependencies
                if self._states[dependency].status != "enabled"
            ]
            if unavailable:
                self._states[name] = PluginState(
                    "blocked", f"Unavailable dependencies: {', '.join(unavailable)}"
                )
                continue
            try:
                await self.enable(name)
            except Exception:
                logger.exception("Plugin enable failed", name=name)

    async def start(self) -> None:
        """Resolve, load and enable every registered plugin with failure isolation."""
        await self.resolve_dependencies()
        await self.load_all()
        await self.enable_all()

    async def disable(self, name: str) -> None:
        plugin = self._plugins.get(name)
        if not plugin:
            raise KeyError(f"Plugin not found: {name}")
        await plugin.on_disable()
        prefix = f"{name}."
        self._extensions = {
            key: value for key, value in self._extensions.items() if not key.startswith(prefix)
        }
        self._states[name] = PluginState("disabled")

    async def disable_all(self) -> None:
        for name in reversed(self._load_order):
            if self._states[name].status == "enabled":
                try:
                    await self.disable(name)
                except Exception as exc:
                    self._states[name] = PluginState("error", str(exc))
                    logger.exception("Plugin shutdown failed", name=name)

    def get_extension(self, name: str) -> Any | None:
        return self._extensions.get(name)

    def get_plugin(self, name: str) -> PluginProtocol | None:
        return self._plugins.get(name)

    def health(self) -> dict[str, dict[str, Any]]:
        health: dict[str, dict[str, Any]] = {
            name: {
                "version": self._plugins[name].version,
                "status": state.status,
                "error": state.error,
                "dependencies": self._plugins[name].dependencies,
            }
            for name, state in self._states.items()
        }
        health.update(
            {
                name: {
                    "version": None,
                    "status": "error",
                    "error": error,
                    "dependencies": [],
                }
                for name, error in self._discovery_errors.items()
            }
        )
        return health
