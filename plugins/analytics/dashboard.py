"""仪表板数据 API"""


class DashboardService:
    """仪表板数据服务"""

    def __init__(self, collector=None, aggregator=None, calculator=None):
        self._collector = collector
        self._aggregator = aggregator
        self._calculator = calculator

    def get_overview(self) -> dict:
        if not self._collector:
            return {"message": "Analytics not configured"}
        records = self._collector.get_today()
        daily = self._aggregator.summary(records) if self._aggregator else {}
        return {"daily": daily}

    def get_token_usage(self, days: int = 7) -> dict:
        if not self._collector or not self._aggregator:
            return {}
        records = self._collector.get_all()
        return self._aggregator.aggregate_daily(records)

    def get_cost_breakdown(self) -> dict:
        if not self._collector or not self._aggregator:
            return {}
        records = self._collector.get_all()
        return self._aggregator.aggregate_by_provider(records)
