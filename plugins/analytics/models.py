"""Analytics 数据模型"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UsageRecord:
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = ""
    provider: str = ""
    model: str = ""
    request_type: str = "chat"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    tool_calls_count: int = 0
