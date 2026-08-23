"""Application-neutral assembly for the plugin runtime."""

from dataclasses import dataclass
from typing import Any

from core.di_container import DIContainer
from core.plugin_manager import PluginManager


@dataclass(frozen=True)
class RuntimeComponents:
    """Single-owner runtime objects published to lifecycle plugins."""

    model_router: Any
    agent_engine: Any
    tool_dispatcher: Any
    content_filter: Any
    execution_guard: Any
    output_guard: Any
    tool_approval: Any
    session_store: Any
    long_term_memory: Any
    memory_consolidator: Any
    metrics_collector: Any
    trace_collector: Any
    audit_log: Any

    def _registrations(self) -> tuple[tuple[str, Any], ...]:
        return (
            ("ModelRouter", self.model_router),
            ("AgentEngine", self.agent_engine),
            ("ToolDispatcher", self.tool_dispatcher),
            ("ContentFilter", self.content_filter),
            ("ExecutionGuard", self.execution_guard),
            ("OutputGuard", self.output_guard),
            ("ToolApproval", self.tool_approval),
            ("SessionStore", self.session_store),
            ("LongTermMemory", self.long_term_memory),
            ("MemoryConsolidator", self.memory_consolidator),
            ("MetricsCollector", self.metrics_collector),
            ("TraceCollector", self.trace_collector),
            ("AuditLog", self.audit_log),
        )


@dataclass(frozen=True)
class PluginActivation:
    discovered: list[str]
    usage_collector: Any | None
    usage_aggregator: Any | None
    cost_calculator: Any | None


async def activate_plugins(
    manager: PluginManager,
    container: DIContainer,
    components: RuntimeComponents,
) -> PluginActivation:
    """Publish composed components, then discover and start runtime plugins."""
    for component_name, component in components._registrations():
        container.register(component_name, component)
    discovered = await manager.discover_and_register()
    await manager.start()
    return PluginActivation(
        discovered=discovered,
        usage_collector=manager.get_extension("analytics.collector"),
        usage_aggregator=manager.get_extension("analytics.aggregator"),
        cost_calculator=manager.get_extension("analytics.cost_calculator"),
    )
