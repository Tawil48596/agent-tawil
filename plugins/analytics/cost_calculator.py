"""成本计算器 — 按模型定价"""


class CostCalculator:
    """LLM 成本计算"""

    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "claude-sonnet-4": {"input": 3.00, "output": 15.00},
        "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
        "deepseek-v4-pro": {"input": 0.14, "output": 0.28},
    }

    def calculate(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = self.PRICING.get(model, {"input": 1.0, "output": 5.0})
        cost = (prompt_tokens / 1_000_000) * pricing["input"] + (
            completion_tokens / 1_000_000
        ) * pricing["output"]
        return round(cost, 6)

    def estimate_budget(self, records: list) -> dict:
        """估算预算使用情况"""
        total = sum(self.calculate(r.model, r.prompt_tokens, r.completion_tokens) for r in records)
        return {
            "total_cost": round(total, 4),
            "record_count": len(records),
            "projected_monthly": round(total * 30, 2) if records else 0,
        }
