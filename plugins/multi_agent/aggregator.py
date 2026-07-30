"""结果聚合器 — 汇总子代理输出"""

from typing import Any


class ResultAggregator:
    """子代理结果聚合器"""

    def __init__(self, model_router=None):
        self._router = model_router

    def aggregate_concat(self, results: list[dict]) -> str:
        """简单拼接"""
        parts = []
        for i, r in enumerate(results, 1):
            text = r.get("result", r.get("error", ""))
            agent_id = r.get("agent_id", r.get("worker_id", f"agent_{i}"))
            parts.append(f"### Agent {agent_id}\n{text}")
        return "\n\n".join(parts)

    def aggregate_summary(self, results: list[dict], max_length: int = 2000) -> str:
        """提取摘要"""
        summaries = []
        for i, r in enumerate(results, 1):
            text = r.get("result", r.get("error", ""))
            agent_id = r.get("agent_id", r.get("worker_id", f"agent_{i}"))
            status = r.get("status", "unknown")
            summaries.append(f"[{status}] {agent_id}: {text[:300]}")
        return "\n".join(summaries)[:max_length]

    async def aggregate_with_llm(self, results: list[dict]) -> str:
        """使用 LLM 智能聚合"""
        combined = self.aggregate_concat(results)
        if not self._router:
            return combined[:3000]

        try:
            from litellm import acompletion
            from plugins.agent_engine.model_router import RouteRequest, TaskType
            route = self._router.route(RouteRequest(task_type=TaskType.SUMMARIZATION))
            response = await acompletion(
                model=f"{route.provider}/{route.model}",
                messages=[{"role": "user", "content": f"总结以下多智能体协作结果:\n\n{combined[:5000]}"}],
                api_key=route.api_key, api_base=route.base_url if route.base_url else None,
                max_tokens=500,
            )
            return response.choices[0].message.content or combined[:1000]
        except Exception:
            return combined[:3000]

    def calculate_stats(self, results: list[dict]) -> dict:
        """计算聚合统计"""
        total = len(results)
        completed = sum(1 for r in results if r.get("status") == "completed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        return {"total": total, "completed": completed, "failed": failed, "success_rate": completed / max(total, 1)}
