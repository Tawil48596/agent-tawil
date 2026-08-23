"""OpenTelemetry 分布式追踪"""

import time
import uuid


class TraceSpan:
    def __init__(self, name: str, span_type: str = "custom", parent=None):
        self.span_id = uuid.uuid4().hex[:8]
        self.parent_id = parent.span_id if parent else None
        self.trace_id = parent.trace_id if parent else uuid.uuid4().hex[:12]
        self.name = name
        self.type = span_type
        self.start_time = time.time()
        self.end_time: float | None = None
        self.attributes: dict = {}
        self.events: list[dict] = []

    def add_event(self, name: str, attributes: dict = None):
        self.events.append({"name": name, "time": time.time(), "attrs": attributes or {}})

    def set_attribute(self, key: str, value):
        self.attributes[key] = value

    def finish(self):
        self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        return ((self.end_time or time.time()) - self.start_time) * 1000


class TracingManager:
    def __init__(self):
        self._traces: dict[str, TraceSpan] = {}
        self._active: dict[str, TraceSpan] = {}
        self._enabled = True

    def start_span(self, name: str, span_type: str = "custom", parent_id: str = None) -> TraceSpan:
        parent = self._active.get(parent_id) if parent_id else None
        span = TraceSpan(name, span_type, parent)
        if not parent:
            self._traces[span.trace_id] = span
        self._active[span.span_id] = span
        return span

    def end_span(self, span: TraceSpan):
        span.finish()
        self._active.pop(span.span_id, None)

    def get_trace(self, trace_id: str) -> TraceSpan | None:
        return self._traces.get(trace_id)

    def list_traces(self, limit: int = 50) -> list:
        return list(self._traces.values())[:limit]
