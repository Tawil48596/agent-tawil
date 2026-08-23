"""群体协作: 动态角色分配"""

import uuid
from collections.abc import Callable


class SwarmPattern:
    """群体模式 — 动态角色分配 + 自组织"""

    async def execute(self, goal: str, agent_count: int = 5, executor: Callable = None) -> dict:
        # 自动分配角色
        roles = ["研究员", "分析师", "评审员", "总结者", "质疑者"]

        agents = []
        for i in range(min(agent_count, len(roles))):
            agents.append(
                {
                    "id": uuid.uuid4().hex[:6],
                    "role": roles[i],
                    "goal": f"你的角色是 {roles[i]}。任务: {goal}",
                }
            )

        results = []
        if executor:
            for agent in agents:
                result = await executor(agent)
                results.append({"agent": agent["role"], "output": result.get("result", "")})

        return {"goal": goal, "swarm_size": len(agents), "results": results}
