"""评测运行器 — CLI + API + CI 集成"""

import json
import os
import time
import uuid
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

    def __init__(
        self,
        suites_dir: str = "plugins/evals/test_suites",
        history_path: str | None = None,
        max_pass_rate_regression: float = 0.0,
        history_limit: int = 100,
    ):
        self._suites_dir = Path(suites_dir)
        self._history_path = Path(history_path) if history_path else None
        self._max_regression = max(0.0, float(max_pass_rate_regression))
        self._history_limit = max(1, int(history_limit))
        self._history = self._load_history()

    def _load_history(self) -> list[dict]:
        if self._history_path is None or not self._history_path.exists():
            return []
        try:
            payload = json.loads(self._history_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Ignoring corrupt eval history", path=str(self._history_path))
            return []
        return payload[-self._history_limit:] if isinstance(payload, list) else []

    def _persist_history(self) -> None:
        if self._history_path is None:
            return
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._history_path.with_name(
            f".{self._history_path.name}.{uuid.uuid4().hex}.tmp"
        )
        try:
            temporary.write_text(
                json.dumps(self._history, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            os.replace(temporary, self._history_path)
        finally:
            temporary.unlink(missing_ok=True)

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
            "run_id": uuid.uuid4().hex,
            "created_at": time.time(),
            "suite": suite_name,
            "total": len(results),
            "passed": passed,
            "pass_rate": passed / max(len(results), 1),
            "elapsed_s": round(elapsed, 1),
            "results": results,
        }
        report["metrics"] = MetricsCalculator().calculate(results).to_dict()

        baseline = next(
            (item for item in reversed(self._history) if item.get("suite") == suite_name),
            None,
        )
        delta = report["pass_rate"] - baseline["pass_rate"] if baseline else 0.0
        report["regression"] = {
            "baseline_found": baseline is not None,
            "baseline_run_id": baseline.get("run_id") if baseline else None,
            "pass_rate_delta": round(delta, 3),
            "max_allowed_regression": self._max_regression,
            "gate_passed": baseline is None or delta >= -self._max_regression,
        }

        self._history.append(report)
        self._history = self._history[-self._history_limit:]
        self._persist_history()
        logger.info("Eval complete", suite=suite_name, pass_rate=report["pass_rate"])
        return report

    def get_history(self, suite: str | None = None, limit: int | None = None) -> list[dict]:
        history = [item for item in self._history if not suite or item.get("suite") == suite]
        return history[-limit:] if limit is not None else history

    def compare_last(self, agent_fn: Callable | None = None) -> Optional[dict]:
        """对比最近两次运行"""
        if not self._history:
            return None
        new = self._history[-1]
        old = next(
            (item for item in reversed(self._history[:-1])
             if item.get("suite") == new.get("suite")),
            None,
        )
        if old is None:
            return None
        return {
            "baseline_pass_rate": old["pass_rate"],
            "new_pass_rate": new["pass_rate"],
            "diff": round(new["pass_rate"] - old["pass_rate"], 3),
            "suite": new["suite"],
        }
