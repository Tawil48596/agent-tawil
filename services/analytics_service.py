"""Analytics Service"""


class AnalyticsService:
    def __init__(self, collector, aggregator, calculator):
        self._collector = collector
        self._aggregator = aggregator
        self._calculator = calculator

    def record_usage(self, **kwargs):
        return self._collector.record(**kwargs)

    def get_summary(self) -> dict:
        records = self._collector.get_all()
        return self._aggregator.summary(records)

    def get_cost_breakdown(self) -> dict:
        records = self._collector.get_all()
        return self._aggregator.aggregate_by_model(records)
