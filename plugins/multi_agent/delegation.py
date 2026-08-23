"""委派引擎 — 创建子代理、传递上下文"""

import uuid
from dataclasses import dataclass, field


@dataclass
class SubAgentConfig:
    goal: str
    context: str = ""
    toolsets: list[str] = field(default_factory=list)
    model: str | None = None
    max_turns: int = 30
    role: str = "leaf"
    timeout: int = 120
    retry_attempts: int = 2
    retry_backoff: str = "exponential"


class DelegationEngine:
    """子代理委派引擎"""

    def __init__(self, agent_engine=None, blackboard=None):
        self._engine = agent_engine
        self._blackboard = blackboard
        self._active_agents: dict[str, dict] = {}

    async def delegate(self, config: SubAgentConfig) -> str:
        """创建子代理，返回 agent_id"""
        agent_id = uuid.uuid4().hex[:8]
        self._active_agents[agent_id] = {
            "config": config,
            "status": "pending",
            "result": None,
        }

        # 写入黑板
        if self._blackboard:
            self._blackboard.write(
                f"agent:{agent_id}:config",
                {
                    "goal": config.goal,
                    "toolsets": config.toolsets,
                    "model": config.model,
                    "max_turns": config.max_turns,
                },
            )

        return agent_id

    async def execute(self, agent_id: str) -> dict:
        """执行子代理任务"""
        agent_info = self._active_agents.get(agent_id)
        if not agent_info:
            return {"error": f"Agent {agent_id} not found"}

        config = agent_info["config"]
        agent_info["status"] = "running"

        if self._engine:
            try:
                import asyncio

                response = await asyncio.wait_for(
                    self._engine.run(
                        user_message=config.goal,
                        override_model=config.model,
                        history=[{"role": "system", "content": config.context}],
                    ),
                    timeout=config.timeout,
                )
                agent_info["status"] = "completed"
                agent_info["result"] = response.text
                if self._blackboard:
                    self._blackboard.write(f"agent:{agent_id}:result", response.text)
                return {"agent_id": agent_id, "status": "completed", "result": response.text}
            except Exception as e:
                agent_info["status"] = "failed"
                agent_info["result"] = str(e)
                return {"agent_id": agent_id, "status": "failed", "error": str(e)}

        agent_info["status"] = "completed"
        agent_info["result"] = f"[Simulated] {config.goal}"
        return {"agent_id": agent_id, "status": "completed", "result": agent_info["result"]}

    def get_status(self, agent_id: str) -> dict | None:
        return self._active_agents.get(agent_id)

    def list_active(self) -> list[dict]:
        return [
            {"id": aid, "status": info["status"], "goal": info["config"].goal}
            for aid, info in self._active_agents.items()
        ]
