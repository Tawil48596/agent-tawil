"""聚合器 — 小时/天/月汇总"""

from collections import defaultdict
from datetime import datetime
from typing import Any


class UsageAggregator:
    """用量数据聚合"""

    def aggregate_daily(self, records: list) -> dict:
        """按天聚合"""
        by_date = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0})
        for r in records:
            date_key = r.timestamp.strftime("%Y-%m-%d")
            by_date[date_key]["tokens"] += r.total_tokens
            by_date[date_key]["cost"] += r.cost
            by_date[date_key]["requests"] += 1
        return dict(by_date)

    def aggregate_by_model(self, records: list) -> dict:
        """按模型聚合"""
        by_model = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0, "provider": ""})
        for r in records:
            by_model[r.model]["tokens"] += r.total_tokens
            by_model[r.model]["cost"] += r.cost
            by_model[r.model]["requests"] += 1
            by_model[r.model]["provider"] = r.provider
        return dict(by_model)

    def aggregate_by_provider(self, records: list) -> dict:
        by_provider = defaultdict(lambda: {"tokens": 0, "cost": 0.0, "requests": 0})
        for r in records:
            by_provider[r.provider]["tokens"] += r.total_tokens
            by_provider[r.provider]["cost"] += r.cost
            by_provider[r.provider]["requests"] += 1
        return dict(by_provider)

    def summary(self, records: list) -> dict:
        if not records:
            return {"total_tokens": 0, "total_cost": 0, "total_requests": 0, "avg_latency_ms": 0}
        return {
            "total_tokens": sum(r.total_tokens for r in records),
            "total_cost": round(sum(r.cost for r in records), 4),
            "total_requests": len(records),
            "avg_latency_ms": int(sum(r.latency_ms for r in records) / len(records)),
        }
