"""Observability Plugin"""

from core.protocols import PluginProtocol


class ObservabilityPlugin(PluginProtocol):
    @property
    def name(self) -> str:
        return "observability"

    @property
    def version(self) -> str:
        return "0.1.1"

    async def on_load(self, container):
        if container is None:
            raise RuntimeError("Observability plugin requires the runtime container")
        self.metrics = container.resolve("MetricsCollector")
        self.traces = container.resolve("TraceCollector")
        self.audit = container.resolve("AuditLog")

    def get_extensions(self):
        return {"metrics": self.metrics, "traces": self.traces, "audit": self.audit}


def create_plugin() -> ObservabilityPlugin:
    return ObservabilityPlugin()
