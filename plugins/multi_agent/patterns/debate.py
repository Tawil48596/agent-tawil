"""辩论协作: 多代理讨论达成共识"""

from collections.abc import Callable


class DebatePattern:
    """辩论模式 — 多轮讨论，每轮各代理提出观点，最终聚合"""

    async def execute(
        self, topic: str, agents: list[dict], rounds: int = 3, executor: Callable = None
    ) -> dict:
        discussion = [f"辩题: {topic}"]
        for r in range(rounds):
            round_results = []
            for agent in agents:
                prompt = (
                    f"辩题: {topic}\n\n已有讨论:\n"
                    + "\n".join(discussion[-10:])
                    + f"\n\n你作为 {agent['role']}，请发表你的观点 (第{r + 1}轮):"
                )
                if executor:
                    result = await executor({"goal": prompt, "role": agent["role"]})
                    round_results.append({"role": agent["role"], "view": result.get("result", "")})
            discussion.extend([f"[{r['role']}]: {r['view'][:200]}" for r in round_results])

        return {"topic": topic, "rounds": rounds, "discussion": discussion[-20:]}
