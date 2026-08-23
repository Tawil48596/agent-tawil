"""生命周期管理 — 创建/监控/终止子代理"""

import contextlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentLifecycle:
    agent_id: str
    status: str = "created"
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class LifecycleManager:
    """Agent 生命周期管理器"""

    def __init__(self):
        self._agents: dict[str, AgentLifecycle] = {}
        self._on_status_change: list[Callable] = []

    def create(self, agent_id: str = "", metadata: dict = None) -> str:
        import uuid

        aid = agent_id or uuid.uuid4().hex[:8]
        self._agents[aid] = AgentLifecycle(agent_id=aid, metadata=metadata or {})
        return aid

    def start(self, agent_id: str) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = "running"
            agent.started_at = time.time()
            self._notify(agent_id, "started")

    def complete(self, agent_id: str, result: Any = None) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = "completed"
            agent.completed_at = time.time()
            self._notify(agent_id, "completed")

    def fail(self, agent_id: str, error: str) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = "failed"
            agent.error = error
            agent.completed_at = time.time()
            self._notify(agent_id, "failed")

    def cancel(self, agent_id: str) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = "cancelled"
            self._notify(agent_id, "cancelled")

    def get(self, agent_id: str) -> AgentLifecycle | None:
        return self._agents.get(agent_id)

    def list_all(self) -> list[AgentLifecycle]:
        return list(self._agents.values())

    def on_status_change(self, callback: Callable) -> None:
        self._on_status_change.append(callback)

    def _notify(self, agent_id: str, status: str) -> None:
        for cb in self._on_status_change:
            with contextlib.suppress(Exception):
                cb(agent_id, status)
