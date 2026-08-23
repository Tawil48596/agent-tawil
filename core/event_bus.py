"""事件总线 — 发布/订阅"""

import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class Event:
    type: str
    source: str
    trace_id: str = ""
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[Event], Any]


class EventBus:
    """发布/订阅事件总线"""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[Event] = []
        self._max_history = 500

    async def publish(self, event: Event) -> None:
        """发布事件到所有订阅者"""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        handlers = self._subscribers.get(event.type, []) + self._subscribers.get("*", [])
        for handler in handlers:
            try:
                import inspect

                if inspect.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.warning("Event handler error", event_type=event.type, error=str(e))

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """订阅事件类型"""
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """取消订阅"""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def get_history(self, event_type: str = "", limit: int = 50) -> list[Event]:
        if event_type:
            return [e for e in self._history if e.type == event_type][-limit:]
        return self._history[-limit:]


# ── 预定义事件类型 ──
AGENT_TURN_START = "agent.turn.start"
AGENT_TURN_END = "agent.turn.end"
TOOL_CALL_BEFORE = "tool.call.before"
TOOL_CALL_AFTER = "tool.call.after"
SESSION_CREATED = "session.created"
SESSION_UPDATED = "session.updated"
SESSION_DELETED = "session.deleted"
MEMORY_SAVED = "memory.saved"
MEMORY_RETRIEVED = "memory.retrieved"
RAG_INDEXED = "rag.indexed"
LLM_REQUEST = "llm.request"
LLM_RESPONSE = "llm.response"
