"""Trace Viewer — 调用链可视化 + 慢动作回放"""

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import structlog
from shared.versioned_store import (
    UnsupportedSchemaVersion,
    load_collection,
    write_collection,
)

logger = structlog.get_logger()


@dataclass
class TraceSpan:
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    parent_id: Optional[str] = None
    trace_id: str = ""
    type: str = "llm_call"    # llm_call | tool_call | agent_think | rag_retrieval | workflow
    name: str = ""
    model: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    error: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list["TraceSpan"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "trace_id": self.trace_id,
            "type": self.type,
            "name": self.name,
            "model": self.model,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children],
        }


class TraceCollector:
    """Trace 收集器 — 记录完整调用链"""

    def __init__(self, max_traces: int = 1000, storage_path: str | None = None):
        self._traces: dict[str, TraceSpan] = {}  # trace_id → root span
        self._max_traces = max_traces
        self._active_spans: dict[str, TraceSpan] = {}  # span_id → span
        self._storage_path = Path(storage_path) if storage_path else None
        self._load()

    @classmethod
    def _from_dict(cls, data: dict) -> TraceSpan:
        children = [cls._from_dict(child) for child in data.get("children", [])]
        fields = {key: value for key, value in data.items() if key != "children"}
        return TraceSpan(**fields, children=children)

    def _load(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        try:
            payload = load_collection(self._storage_path)
            traces = [self._from_dict(item) for item in payload if isinstance(item, dict)]
            self._traces = {trace.trace_id: trace for trace in traces[-self._max_traces:]}
        except UnsupportedSchemaVersion:
            raise
        except (OSError, TypeError, ValueError):
            logger.warning("Ignoring corrupt trace history", path=str(self._storage_path))

    def _persist(self) -> None:
        if self._storage_path is None:
            return
        write_collection(
            self._storage_path, [trace.to_dict() for trace in self._traces.values()]
        )

    def start_trace(self, name: str = "agent_run", trace_type: str = "workflow",
                    trace_id: str | None = None) -> TraceSpan:
        """开始一个新的 Trace"""
        trace_id = trace_id or uuid.uuid4().hex[:12]
        root = TraceSpan(
            span_id=trace_id,
            trace_id=trace_id,
            type=trace_type,
            name=name,
        )
        self._traces[trace_id] = root
        self._active_spans[root.span_id] = root
        self._trim()
        return root

    def add_span(self, parent_span: TraceSpan, span_type: str, name: str,
                  model: str = "", input_data: dict = None) -> TraceSpan:
        """添加子 Span"""
        child = TraceSpan(
            parent_id=parent_span.span_id,
            trace_id=parent_span.trace_id,
            type=span_type,
            name=name,
            model=model,
            input=input_data or {},
        )
        parent_span.children.append(child)
        self._active_spans[child.span_id] = child
        return child

    def end_span(self, span: TraceSpan, output: dict = None,
                  tokens_in: int = 0, tokens_out: int = 0,
                  error: str = None):
        """结束 Span"""
        span.output = output or {}
        span.tokens_in = tokens_in
        span.tokens_out = tokens_out
        span.end_time = time.time()
        span.latency_ms = int((span.end_time - span.start_time) * 1000)
        span.error = error
        self._active_spans.pop(span.span_id, None)
        if span.parent_id is None:
            self._persist()

    def get_trace(self, trace_id: str) -> Optional[TraceSpan]:
        return self._traces.get(trace_id)

    def list_traces(
        self, limit: int = 50, error_only: bool = False, min_latency_ms: int = 0
    ) -> list[dict]:
        traces = sorted(self._traces.values(), key=lambda t: t.start_time, reverse=True)
        traces = [
            trace for trace in traces
            if trace.latency_ms >= min_latency_ms
            and (not error_only or self._has_error(trace))
        ]
        return [
            {
                "trace_id": t.trace_id,
                "name": t.name,
                "type": t.type,
                "start_time": t.start_time,
                "span_count": self._count_spans(t),
                "total_latency_ms": t.latency_ms,
                "total_tokens": t.tokens_in + t.tokens_out,
                "has_error": any(self._has_error(c) for c in t.children),
            }
            for t in traces[:limit]
        ]

    def _count_spans(self, span: TraceSpan) -> int:
        return 1 + sum(self._count_spans(c) for c in span.children)

    def _has_error(self, span: TraceSpan) -> bool:
        return span.error is not None or any(self._has_error(c) for c in span.children)

    def _trim(self):
        if len(self._traces) > self._max_traces:
            oldest = sorted(self._traces.values(), key=lambda trace: trace.start_time)
            for trace in oldest[:len(self._traces) - self._max_traces]:
                del self._traces[trace.trace_id]

    def get_stats(self) -> dict:
        total_spans = sum(self._count_spans(t) for t in self._traces.values())
        total_tokens = sum(t.tokens_in + t.tokens_out for t in self._traces.values())
        return {
            "total_traces": len(self._traces),
            "total_spans": total_spans,
            "total_tokens": total_tokens,
            "active_spans": len(self._active_spans),
        }
