"""代理间通信 — 消息传递协议 + 共享黑板"""

import contextlib
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger()


class MessageType(StrEnum):
    REQUEST = "request"
    RESPONSE = "response"
    INFORM = "inform"
    ERROR = "error"
    BROADCAST = "broadcast"


@dataclass
class AgentMessage:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    sender_id: str = ""
    receiver_id: str = ""  # "" = broadcast
    type: MessageType = MessageType.INFORM
    content: dict[str, Any] = field(default_factory=dict)
    in_reply_to: str | None = None
    timestamp: float = field(default_factory=time.time)


class MessageBus:
    """代理间消息总线"""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}  # agent_id → [handlers]
        self._broadcast_handlers: list[Callable] = []
        self._message_log: list[AgentMessage] = []
        self._max_log_size = 1000

    def subscribe(self, agent_id: str, handler: Callable):
        """订阅消息"""
        self._subscribers.setdefault(agent_id, []).append(handler)

    def on_broadcast(self, handler: Callable):
        self._broadcast_handlers.append(handler)

    async def send(self, msg: AgentMessage):
        """发送消息"""
        self._message_log.append(msg)
        if len(self._message_log) > self._max_log_size:
            self._message_log = self._message_log[-self._max_log_size :]

        # 定向发送
        if msg.receiver_id and msg.receiver_id in self._subscribers:
            for handler in self._subscribers[msg.receiver_id]:
                try:
                    if handler.__code__.co_flags & 0x80:  # 是 async
                        await handler(msg)
                    else:
                        handler(msg)
                except Exception as e:
                    logger.warning("Message handler error", agent=msg.receiver_id, error=str(e))

        # 广播
        if not msg.receiver_id:
            for handler in self._broadcast_handlers:
                with contextlib.suppress(Exception):
                    await handler(msg) if handler.__code__.co_flags & 0x80 else handler(msg)

    def get_history(self, agent_id: str = "", limit: int = 50) -> list[AgentMessage]:
        """获取消息历史"""
        if agent_id:
            return [
                m for m in self._message_log if m.sender_id == agent_id or m.receiver_id == agent_id
            ][-limit:]
        return self._message_log[-limit:]


class Blackboard:
    """共享 Key-Value 黑板 — 多智能体中间状态存储"""

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._versions: dict[str, int] = {}
        self._watchers: dict[str, list[Callable]] = {}

    def write(self, key: str, value: Any):
        self._data[key] = value
        self._versions[key] = self._versions.get(key, 0) + 1
        # 通知 watchers
        for watcher in self._watchers.get(key, []):
            with contextlib.suppress(Exception):
                watcher(key, value)

    def read(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def read_all(self, prefix: str = "") -> dict[str, Any]:
        if prefix:
            return {k: v for k, v in self._data.items() if k.startswith(prefix)}
        return dict(self._data)

    def delete(self, key: str):
        self._data.pop(key, None)
        self._versions.pop(key, None)

    def watch(self, key: str, callback: Callable):
        self._watchers.setdefault(key, []).append(callback)

    def get_version(self, key: str) -> int:
        return self._versions.get(key, 0)

    def snapshot(self, task_id: str) -> dict:
        """创建任务相关的状态快照"""
        return {key: val for key, val in self._data.items() if task_id in key}

    def restore(self, snapshot: dict):
        """从快照恢复"""
        for key, val in snapshot.items():
            self._data[key] = val

    def clear_task(self, task_id: str):
        """清理任务相关数据"""
        keys = [k for k in self._data if task_id in k]
        for k in keys:
            self.delete(k)
