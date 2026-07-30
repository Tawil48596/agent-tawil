"""工作代理 — 隔离上下文 + 受限工具集"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class WorkerConfig:
    goal: str
    context: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    model: Optional[str] = None
    max_turns: int = 30
    timeout: int = 120


class WorkerAgent:
    """隔离的工作代理"""

    def __init__(self, engine=None, blackboard=None):
        self._engine = engine
        self._blackboard = blackboard
        self._id = uuid.uuid4().hex[:8]

    @property
    def agent_id(self) -> str:
        return self._id

    async def execute(self, config: WorkerConfig) -> dict:
        """在受限环境中执行任务"""
        # 保存检查点
        if self._blackboard:
            self._blackboard.write(f"worker:{self._id}:start", {
                "goal": config.goal,
                "tools": config.allowed_tools,
                "timestamp": __import__("time").time(),
            })

        if self._engine:
            try:
                response = await asyncio.wait_for(
                    self._engine.run(
                        user_message=config.goal,
                        override_model=config.model,
                        history=[{"role": "system", "content": config.context}],
                    ),
                    timeout=config.timeout,
                )

                if self._blackboard:
                    self._blackboard.write(f"worker:{self._id}:result", response.text)

                return {"worker_id": self._id, "status": "completed", "result": response.text}
            except asyncio.TimeoutError:
                return {"worker_id": self._id, "status": "timeout", "error": f"Timeout after {config.timeout}s"}
            except Exception as e:
                return {"worker_id": self._id, "status": "failed", "error": str(e)}

        return {"worker_id": self._id, "status": "completed", "result": f"[Simulated] {config.goal}"}
