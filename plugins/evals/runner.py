"""评测运行器 — CLI + API + CI 集成"""

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import structlog
import yaml

from plugins.evals.metrics import MetricsCalculator

logger = structlog.get_logger()


@dataclass
class TestSuite:
    name: str
    description: str = ""
    cases: list[dict] = field(default_factory=list)


class EvalRunner:
    """评测运行器"""

    def __init__(self, suites_dir: str = "plugins/evals/test_suites"):
        self._suites_dir = Path(suites_dir)
        self._history: list[dict] = []

    def load_suite(self, name: str) -> Optional[TestSuite]:
        """从 YAML 文件加载测试集"""
        path = self._suites_dir / f"{name}.yaml"
        if not path.exists():
            path = self._suites_dir / f"{name}.yml"
        if not path.exists():
            return None

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return TestSuite(
            name=data.get("name", name),
            description=data.get("description", ""),
            cases=data.get("cases", []),
        )

    def list_suites(self) -> list[str]:
        if not self._suites_dir.exists():
            return []
        return [p.stem for p in self._suites_dir.glob("*.yaml")] + \
               [p.stem for p in self._suites_dir.glob("*.yml")]

    async def run(self, suite_name: str, agent_fn: Callable,
                   judge=None) -> dict:
        """运行评测"""
        suite = self.load_suite(suite_name)
        if not suite:
            return {"error": f"Suite not found: {suite_name}"}

        start = time.time()
        results = []

        for case_data in suite.cases:
            try:
                case_start = time.time()
                output = await agent_fn(case_data.get("input", ""))
                case_time = time.time() - case_start

                # 简单断言
                expected = case_data.get("expected", {})
                structured = output if isinstance(output, dict) else {"text": str(output)}
                text = str(structured.get("text", ""))
                actual_tools = list(structured.get("tools", []))
                usage = structured.get("usage", {}) or {}

                kw = expected.get("keywords", [])
                kw_matched = [k for k in kw if k.lower() in text.lower()]
                keyword_score = len(kw_matched) / len(kw) if kw else 1.0
                expected_tools = list(expected.get("tools", []))
                tool_accuracy = (
                    len(set(actual_tools) & set(expected_tools))
                    / len(set(actual_tools) | set(expected_tools))
                    if actual_tools or expected_tools else 1.0
                )
                passed = keyword_score >= 0.5 and tool_accuracy == 1.0

                results.append({
                    "case": case_data.get("id", ""),
                    "passed": passed,
                    "latency_ms": round(case_time * 1000),
                    "keywords_matched": kw_matched,
                    "keywords_expected": kw,
                    "tools_actual": actual_tools,
                    "tools_expected": expected_tools,
                    "tool_accuracy": round(tool_accuracy, 3),
                    "score": round((keyword_score + tool_accuracy) / 2, 3),
                    "total_tokens": int(usage.get("total_tokens", 0) or 0),
                })
            except Exception as e:
                results.append({
                    "case": case_data.get("id", ""),
                    "passed": False,
                    "error": str(e),
                })

        elapsed = time.time() - start
        passed = sum(1 for r in results if r["passed"])
        report = {
            "suite": suite_name,
            "total": len(results),
            "passed": passed,
            "pass_rate": passed / max(len(results), 1),
            "elapsed_s": round(elapsed, 1),
            "results": results,
        }
        report["metrics"] = MetricsCalculator().calculate(results).to_dict()

        self._history.append(report)
        logger.info("Eval complete", suite=suite_name, pass_rate=report["pass_rate"])
        return report

    def get_history(self) -> list[dict]:
        return self._history

    def compare_last(self, agent_fn: Callable) -> Optional[dict]:
        """对比最近两次运行"""
        if len(self._history) < 2:
            return None
        old = self._history[-2]
        new = self._history[-1]
        return {
            "baseline_pass_rate": old["pass_rate"],
            "new_pass_rate": new["pass_rate"],
            "diff": round(new["pass_rate"] - old["pass_rate"], 3),
            "suite": new["suite"],
        }
