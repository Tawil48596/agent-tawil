"""Prometheus 指标暴露"""

from collections import defaultdict


class MetricsCollector:
    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = defaultdict(float)
        self._histograms: dict[str, list] = defaultdict(list)

    def inc(self, name: str, value: int = 1):
        self._counters[name] += value

    def set_gauge(self, name: str, value: float):
        self._gauges[name] = value

    def observe(self, name: str, value: float):
        self._histograms[name].append(value)

    def record_tool_event(self, event_type: str, **fields) -> None:
        """Convert bounded tool lifecycle events into aggregate metrics."""
        known_events = {
            "tool.started",
            "tool.completed",
            "tool.failed",
            "tool.timeout",
            "tool.replayed",
            "tool.approval_required",
            "tool.approval_denied",
            "tool.approval_approved",
        }
        if event_type not in known_events:
            return
        self.inc(f"{event_type.replace('.', '_')}_total")
        if "duration_ms" in fields:
            self.observe("tool_execution_duration_ms", float(fields["duration_ms"]))

    def record_llm_usage(self, usage: dict) -> None:
        """Aggregate normalized LLM usage without prompts or model output."""
        self.inc("llm_requests_total", int(usage.get("requests", 0) or 0))
        for key in (
            "input_tokens",
            "cached_input_tokens",
            "cache_write_input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "total_tokens",
        ):
            self.inc(f"llm_{key}_total", int(usage.get(key, 0) or 0))

    def get_all(self) -> dict:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: {"count": len(v), "avg": sum(v) / max(len(v), 1)}
                for k, v in self._histograms.items()
            },
        }
