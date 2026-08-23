from pathlib import Path

import pytest

from core.di_container import DIContainer
from core.plugin_manager import PluginManager
from core.protocols import PluginProtocol


class Plugin(PluginProtocol):
    def __init__(self, name, dependencies=None, *, fail_at=None):
        self._name = name
        self._dependencies = dependencies or []
        self.fail_at = fail_at
        self.events = []

    @property
    def name(self):
        return self._name

    @property
    def dependencies(self):
        return self._dependencies

    async def on_load(self, container):
        self.events.append("load")
        if self.fail_at == "load":
            raise RuntimeError("load exploded")

    async def on_enable(self):
        self.events.append("enable")
        if self.fail_at == "enable":
            raise RuntimeError("enable exploded")

    async def on_disable(self):
        self.events.append("disable")
        if self.fail_at == "disable":
            raise RuntimeError("disable exploded")

    def get_extensions(self):
        return {"value": self.name}


@pytest.mark.asyncio
async def test_plugin_lifecycle_and_health():
    manager = PluginManager([], container=DIContainer())
    base, child = Plugin("base"), Plugin("child", ["base"])
    manager.register(child)
    manager.register(base)
    assert await manager.resolve_dependencies() == ["base", "child"]
    await manager.load_all()
    await manager.enable_all()
    assert manager.get_extension("child.value") == "child"
    assert manager.health()["base"]["status"] == "enabled"
    await manager.disable_all()
    assert manager.health()["child"]["status"] == "disabled"


@pytest.mark.asyncio
async def test_missing_dependency_is_rejected():
    manager = PluginManager([])
    manager.register(Plugin("child", ["missing"]))
    with pytest.raises(RuntimeError, match="Missing"):
        await manager.resolve_dependencies()


@pytest.mark.asyncio
async def test_start_isolates_failure_and_blocks_only_dependants():
    manager = PluginManager([], container=DIContainer())
    broken = Plugin("broken", fail_at="load")
    dependant = Plugin("dependant", ["broken"])
    independent = Plugin("independent")
    for plugin in (dependant, broken, independent):
        manager.register(plugin)

    await manager.start()

    health = manager.health()
    assert health["broken"]["status"] == "error"
    assert health["dependant"]["status"] == "blocked"
    assert "broken" in health["dependant"]["error"]
    assert health["independent"]["status"] == "enabled"
    assert manager.get_extension("independent.value") == "independent"


@pytest.mark.asyncio
async def test_discover_and_register_uses_explicit_entrypoint(tmp_path):
    plugin_dir = tmp_path / "plugins" / "sample"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.py").write_text(
        """
from core.protocols import PluginProtocol

class SamplePlugin(PluginProtocol):
    @property
    def name(self):
        return "sample"

    def get_extensions(self):
        return {"answer": 42}

def create_plugin():
    return SamplePlugin()
""",
        encoding="utf-8",
    )
    manager = PluginManager([str(tmp_path / "plugins")], container=DIContainer())

    assert await manager.discover_and_register() == ["sample"]
    await manager.start()

    assert manager.health()["sample"]["status"] == "enabled"
    assert manager.get_extension("sample.answer") == 42


@pytest.mark.asyncio
async def test_discovery_failure_does_not_block_independent_plugin(tmp_path):
    broken_dir = tmp_path / "plugins" / "broken"
    healthy_dir = tmp_path / "plugins" / "healthy"
    broken_dir.mkdir(parents=True)
    healthy_dir.mkdir(parents=True)
    (broken_dir / "plugin.py").write_text("raise RuntimeError('import exploded')", encoding="utf-8")
    (healthy_dir / "plugin.py").write_text(
        """
from core.protocols import PluginProtocol

class HealthyPlugin(PluginProtocol):
    @property
    def name(self):
        return "healthy"

def create_plugin():
    return HealthyPlugin()
""",
        encoding="utf-8",
    )
    manager = PluginManager([str(tmp_path / "plugins")], container=DIContainer())

    assert await manager.discover_and_register() == ["healthy"]
    await manager.start()

    assert manager.health()["broken"]["status"] == "error"
    assert manager.health()["healthy"]["status"] == "enabled"


@pytest.mark.asyncio
async def test_circular_dependency_is_rejected():
    manager = PluginManager([])
    manager.register(Plugin("first", ["second"]))
    manager.register(Plugin("second", ["first"]))

    with pytest.raises(RuntimeError, match="Circular"):
        await manager.resolve_dependencies()


@pytest.mark.asyncio
async def test_builtin_plugins_expose_the_composed_runtime_instances():
    container = DIContainer()
    component_names = [
        "ModelRouter",
        "AgentEngine",
        "ToolDispatcher",
        "ContentFilter",
        "ExecutionGuard",
        "OutputGuard",
        "ToolApproval",
        "SessionStore",
        "LongTermMemory",
        "MemoryConsolidator",
        "MetricsCollector",
        "TraceCollector",
        "AuditLog",
    ]
    components = {name: object() for name in component_names}
    for name, component in components.items():
        container.register(name, component)
    plugin_root = Path(__file__).parents[2] / "plugins"
    manager = PluginManager([str(plugin_root)], container=container)

    discovered = await manager.discover_and_register()
    await manager.start()

    assert discovered == [
        "agent-engine",
        "analytics",
        "conversation",
        "memory",
        "observability",
        "security",
    ]
    assert all(item["status"] == "enabled" for item in manager.health().values())
    assert manager.get_extension("agent-engine.agent_engine") is components["AgentEngine"]
    assert manager.get_extension("security.tool_approval") is components["ToolApproval"]
