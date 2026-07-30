"""Prometheus 指标暴露"""

from collections import defaultdict


class MetricsCollector:
    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list] = defaultdict(list)

    def inc(self, name: str, value: int = 1): self._counters[name] += value
    def set_gauge(self, name: str, value: float): self._gauges[name] = value
    def observe(self, name: str, value: float): self._histograms[name].append(value)

    def get_all(self) -> dict:
        return {"counters": dict(self._counters), "gauges": dict(self._gauges),
                "histograms": {k: {"count": len(v), "avg": sum(v)/max(len(v),1)} for k, v in self._histograms.items()}}
