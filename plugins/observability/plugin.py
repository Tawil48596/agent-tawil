"""Observability Plugin"""

from core.protocols import PluginProtocol


class ObservabilityPlugin(PluginProtocol):
    @property
    def name(self) -> str: return "observability"
    @property
    def version(self) -> str: return "0.1.1"

    async def on_load(self, container):
        from plugins.observability.tracing import TracingManager
        from plugins.observability.health_check import HealthChecker
        from plugins.observability.metrics import MetricsCollector
        self.tracing = TracingManager()
        self.health = HealthChecker()
        self.metrics = MetricsCollector()
        container.register("TracingManager", self.tracing)
        container.register("HealthChecker", self.health)
