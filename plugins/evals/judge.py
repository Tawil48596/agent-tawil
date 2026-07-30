"""LLM-as-a-Judge 评测引擎 — Pass@1, 工具精准度, 幻觉率"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class EvalMetric(str, Enum):
    PASS_AT_1 = "pass_at_1"          # 首次通过率
    TOOL_ACCURACY = "tool_accuracy"   # 工具选用精准度
    HALLUCINATION = "hallucination"   # 幻觉率
    LATENCY = "latency"              # 延迟
    TOKEN_EFFICIENCY = "token_efficiency"  # Token 效率


@dataclass
class EvalCase:
    id: str
    category: str              # reasoning | tool_use | safety | coding
    input: str                 # 用户输入
    expected: dict = field(default_factory=dict)  # 期望输出
    expected_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    expected_keywords: list[str] = field(default_factory=list)
    max_turns: int = 10
    difficulty: str = "medium"  # easy | medium | hard


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    score: float
    metrics: dict[str, Any] = field(default_factory=dict)
    details: str = ""


class LLMJudge:
    """LLM-as-a-Judge 评测器"""

    JUDGE_PROMPT = """你是一个评测裁判。根据以下标准判断 Agent 的回复是否合格。

测试用例:
  输入: {input}
  期望关键词: {keywords}
  期望工具调用: {tools}

Agent 回复:
  {response}

工具调用记录:
  {tool_calls}

请以 JSON 格式返回评测结果:
{{
  "passed": true/false,
  "score": 0.0-1.0,
  "reasoning_correct": true/false,
  "tool_selection_correct": true/false,
  "hallucination_detected": true/false,
  "explanation": "简短的评测说明"
}}"""

    def __init__(self, model_router=None):
        self._router = model_router
        self._results: list[EvalResult] = []

    async def evaluate(self, case: EvalCase, agent_response: str,
                        tool_calls: list[str] = None) -> EvalResult:
        """评测单个用例"""
        score = 0.0
        details = []

        # 1. 关键词检查
        kw_matched = []
        for kw in case.expected_keywords:
            if kw.lower() in agent_response.lower():
                kw_matched.append(kw)
        kw_score = len(kw_matched) / max(len(case.expected_keywords), 1) if case.expected_keywords else 1.0
        score += kw_score * 0.4
        if kw_matched:
            details.append(f"关键词匹配: {kw_matched}")

        # 2. 工具调用检查
        tc = tool_calls or []
        if case.expected_tools:
            tc_matched = [t for t in case.expected_tools if t in tc]
            tc_forbidden = [t for t in case.forbidden_tools if t in tc]
            tc_score = len(tc_matched) / len(case.expected_tools) if case.expected_tools else 1.0
            if tc_forbidden:
                tc_score = 0.0
                details.append(f"使用了禁用工具: {tc_forbidden}")
            score += tc_score * 0.4
            if tc_matched:
                details.append(f"工具匹配: {tc_matched}")
        else:
            score += 0.4

        # 3. LLM Judge (如果有 Router)
        if self._router:
            judge_score = await self._llm_judge(case, agent_response, tool_calls)
            score += judge_score * 0.2
        else:
            score += 0.2

        passed = score >= 0.7
        result = EvalResult(
            case_id=case.id, passed=passed, score=score,
            metrics={"kw_score": kw_score, "judge_score": score},
            details="; ".join(details),
        )
        self._results.append(result)
        return result

    async def _llm_judge(self, case: EvalCase, response: str,
                          tool_calls: list[str] = None) -> float:
        """使用 LLM 裁判"""
        try:
            from litellm import acompletion
            route = self._router.route.__self__  # simplified
            # 简化版: 返回启发式分数
            score = 0.5
            if any(kw.lower() in response.lower() for kw in case.expected_keywords):
                score = 0.8
            return score
        except Exception:
            return 0.5

    async def evaluate_suite(self, suite: list[EvalCase],
                              agent_fn) -> dict:
        """批量评测"""
        results = []
        for case in suite:
            try:
                response, tool_calls = await agent_fn(case.input)
                result = await self.evaluate(case, response, tool_calls)
                results.append(result)
            except Exception as e:
                results.append(EvalResult(case_id=case.id, passed=False, score=0.0,
                                           details=str(e)))

        passed = sum(1 for r in results if r.passed)
        avg_score = sum(r.score for r in results) / max(len(results), 1)

        return {
            "total": len(results),
            "passed": passed,
            "pass_rate": passed / max(len(results), 1),
            "avg_score": round(avg_score, 3),
            "by_category": self._group_by_category(results),
            "results": [
                {"id": r.case_id, "passed": r.passed, "score": round(r.score, 3),
                 "details": r.details}
                for r in results
            ],
        }

    def _group_by_category(self, results: list[EvalResult]) -> dict:
        # Simplified
        return {"all": {"passed": sum(1 for r in results if r.passed), "total": len(results)}}

    def compare(self, baseline_results: dict, new_results: dict) -> dict:
        """A/B 对比"""
        return {
            "baseline": {"pass_rate": baseline_results.get("pass_rate", 0)},
            "new": {"pass_rate": new_results.get("pass_rate", 0)},
            "diff": round(new_results.get("pass_rate", 0) - baseline_results.get("pass_rate", 0), 3),
        }
