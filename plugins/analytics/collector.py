"""数据采集器 — 每次 LLM 调用记录"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UsageRecord:
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    provider: str = ""
    model: str = ""
    request_type: str = "chat"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    tool_calls_count: int = 0


class UsageCollector:
    """用量数据收集器"""

    def __init__(self):
        self._records: list[UsageRecord] = []

    def record(self, **kwargs) -> UsageRecord:
        record = UsageRecord(**kwargs)
        self._records.append(record)
        return record

    def get_today(self) -> list[UsageRecord]:
        today = datetime.now().date()
        return [r for r in self._records if r.timestamp.date() == today]

    def get_all(self, limit: int = 1000) -> list[UsageRecord]:
        return self._records[-limit:]

    def clear(self) -> None:
        self._records.clear()

    @property
    def count(self) -> int:
        return len(self._records)
