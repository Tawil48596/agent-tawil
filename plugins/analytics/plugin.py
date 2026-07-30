"""Analytics Plugin"""

from core.protocols import PluginProtocol


class AnalyticsPlugin(PluginProtocol):
    @property
    def name(self) -> str:
        return "analytics"

    @property
    def version(self) -> str:
        return "0.1.0"

    async def on_load(self, container):
        from plugins.analytics.collector import UsageCollector
        from plugins.analytics.aggregator import UsageAggregator
        from plugins.analytics.cost_calculator import CostCalculator
        self.collector = UsageCollector()
        self.aggregator = UsageAggregator()
        self.calculator = CostCalculator()
        container.register("UsageCollector", self.collector)
        container.register("UsageAggregator", self.aggregator)

    def get_extensions(self):
        return {"collector": self.collector, "aggregator": self.aggregator}
