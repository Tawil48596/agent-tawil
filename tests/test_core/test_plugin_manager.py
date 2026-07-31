import pytest

from core.di_container import DIContainer
from core.plugin_manager import PluginManager
from core.protocols import PluginProtocol


class Plugin(PluginProtocol):
    def __init__(self, name, dependencies=None):
        self._name = name
        self._dependencies = dependencies or []
        self.events = []

    @property
    def name(self):
        return self._name

    @property
    def dependencies(self):
        return self._dependencies

    async def on_load(self, container):
        self.events.append("load")

    async def on_enable(self):
        self.events.append("enable")

    async def on_disable(self):
        self.events.append("disable")

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
