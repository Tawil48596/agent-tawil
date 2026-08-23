import pytest

from core.di_container import DIContainer
from core.plugin_manager import PluginManager
from core.protocols import PluginProtocol
from core.runtime_assembly import RuntimeComponents, activate_plugins
from core.service_lifecycle import shutdown_services


class RuntimePlugin(PluginProtocol):
    def __init__(self, name="runtime", extensions=None):
        self._name = name
        self._extensions = extensions or {}

    @property
    def name(self):
        return self._name

    def get_extensions(self):
        return self._extensions


class AsyncResource:
    def __init__(self, events, name, *, fail=False, configured=True):
        self.events = events
        self.name = name
        self.fail = fail
        self.is_configured = configured

    async def stop(self):
        self.events.append(self.name)
        if self.fail:
            raise RuntimeError(f"{self.name} failed")

    async def disable_all(self):
        await self.stop()


class SyncResource:
    def __init__(self, events):
        self.events = events

    def close(self):
        self.events.append("session_store")


@pytest.mark.asyncio
async def test_runtime_assembly_registers_components_and_starts_plugins():
    container = DIContainer()
    manager = PluginManager([], container=container)
    usage_collector = object()
    usage_aggregator = object()
    cost_calculator = object()
    manager.register(
        RuntimePlugin(
            "analytics",
            {
                "collector": usage_collector,
                "aggregator": usage_aggregator,
                "cost_calculator": cost_calculator,
            },
        )
    )
    marker = object()
    components = RuntimeComponents(
        model_router=marker,
        agent_engine=object(),
        tool_dispatcher=object(),
        content_filter=object(),
        execution_guard=object(),
        output_guard=object(),
        tool_approval=object(),
        session_store=object(),
        long_term_memory=object(),
        memory_consolidator=object(),
        metrics_collector=object(),
        trace_collector=object(),
        audit_log=object(),
    )

    activation = await activate_plugins(manager, container, components)

    assert activation.discovered == []
    assert activation.usage_collector is usage_collector
    assert activation.usage_aggregator is usage_aggregator
    assert activation.cost_calculator is cost_calculator
    assert container.resolve("ModelRouter") is marker
    assert manager.health()["analytics"]["status"] == "enabled"


@pytest.mark.asyncio
async def test_shutdown_attempts_every_resource_after_a_failure():
    events = []

    await shutdown_services(
        plugin_manager=AsyncResource(events, "plugins", fail=True),
        task_queue=AsyncResource(events, "task_queue"),
        session_store=SyncResource(events),
        messaging_adapter=AsyncResource(events, "messaging"),
    )

    assert events == ["plugins", "task_queue", "messaging", "session_store"]
