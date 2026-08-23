"""评测指标: Pass@1, 工具精准度, 幻觉率"""

from dataclasses import dataclass, field
from enum import StrEnum


class EvalMetric(StrEnum):
    PASS_AT_1 = "pass_at_1"
    TOOL_ACCURACY = "tool_accuracy"
    HALLUCINATION = "hallucination"
    LATENCY = "latency"
    TOKEN_EFFICIENCY = "token_efficiency"


@dataclass
class MetricsReport:
    total: int = 0
    passed: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    tool_accuracy: float = 0.0
    argument_accuracy: float = 0.0
    budget_failures: int = 0
    hallucination_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_tokens: int = 0
    by_category: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "pass_rate": round(self.pass_rate, 3),
            "avg_score": round(self.avg_score, 3),
            "tool_accuracy": round(self.tool_accuracy, 3),
            "argument_accuracy": round(self.argument_accuracy, 3),
            "budget_failures": self.budget_failures,
            "hallucination_rate": round(self.hallucination_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "avg_tokens": self.avg_tokens,
            "by_category": self.by_category,
        }


class MetricsCalculator:
    """评测指标计算器"""

    def calculate(self, results: list[dict]) -> MetricsReport:
        if not results:
            return MetricsReport()
        total = len(results)
        passed = sum(1 for r in results if r.get("passed", False))
        scores = [r.get("score", 0) for r in results if "score" in r]
        tool_scores = [r["tool_accuracy"] for r in results if "tool_accuracy" in r]
        argument_scores = [r["argument_accuracy"] for r in results if "argument_accuracy" in r]
        tokens = [int(r.get("total_tokens", 0) or 0) for r in results]
        return MetricsReport(
            total=total,
            passed=passed,
            pass_rate=passed / total if total else 0,
            avg_score=sum(scores) / len(scores) if scores else 0,
            tool_accuracy=sum(tool_scores) / len(tool_scores) if tool_scores else 0,
            argument_accuracy=(
                sum(argument_scores) / len(argument_scores) if argument_scores else 0
            ),
            budget_failures=sum(1 for r in results if not r.get("budget_passed", True)),
            avg_latency_ms=sum(r.get("latency_ms", 0) for r in results) / total,
            avg_tokens=round(sum(tokens) / total),
        )
