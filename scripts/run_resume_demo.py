"""Run the deterministic recovery showcase and write machine-readable evidence."""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import tempfile
from pathlib import Path

from plugins.agent_engine.tool_dispatch import ToolDispatcher
from plugins.checkpoint.execution_ledger import ToolExecutionLedger
from plugins.evals.trace_viewer import TraceCollector
from plugins.hitl.hitl_manager import HITLManager, HITLStatus, HITLType
from scripts.run_offline_eval import run as run_offline_eval

ROOT = Path(__file__).resolve().parents[1]


def _call(call_id: str) -> dict:
    return {
        "id": call_id,
        "function": {"name": "create_artifact", "arguments": '{"name":"demo"}'},
    }


async def run(output: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="agent-resume-demo-") as temporary:
        workspace = Path(temporary)
        ledger_path = workspace / "ledger"
        trace_path = workspace / "traces.json"
        execution_count = 0
        audit_events: list[str] = []

        async def create_artifact(name: str) -> str:
            nonlocal execution_count
            execution_count += 1
            return f"created:{name}:{execution_count}"

        def audit(event_type: str, **_fields) -> None:
            audit_events.append(event_type)

        first = ToolDispatcher()
        first.set_execution_ledger(ToolExecutionLedger(ledger_path))
        first.set_audit_handler(audit)
        first.register("create_artifact", create_artifact)
        initial = (await first.execute_parallel([_call("stable-call")], context={"id": "demo"}))[0]

        restarted = ToolDispatcher()
        restarted.set_execution_ledger(ToolExecutionLedger(ledger_path))
        restarted.set_audit_handler(audit)
        restarted.register("create_artifact", create_artifact)
        replay = (await restarted.execute_parallel([_call("stable-call")], context={"id": "demo"}))[
            0
        ]

        async def uncertain_artifact(name: str) -> str:
            nonlocal execution_count
            execution_count += 1
            raise RuntimeError(f"connection lost after creating {name}")

        restarted.register("create_artifact", uncertain_artifact)
        uncertain = (
            await restarted.execute_parallel([_call("uncertain-call")], context={"id": "demo"})
        )[0]
        after_second_restart = ToolDispatcher()
        ledger = ToolExecutionLedger(ledger_path)
        after_second_restart.set_execution_ledger(ledger)
        after_second_restart.register("create_artifact", create_artifact)
        blocked = (
            await after_second_restart.execute_parallel(
                [_call("uncertain-call")], context={"id": "demo"}
            )
        )[0]

        hitl = HITLManager({"hitl": {"timeout": 2}})

        async def reconcile(request) -> None:
            hitl.approve(request.id)

        hitl.on_request(reconcile)
        decision = await hitl.request(
            "demo",
            HITLType.CONFIRM,
            "Reconcile uncertain tool execution",
            "The external artifact exists; do not retry automatically.",
            proposed_action={"call_id": "uncertain-call", "retry": False},
        )
        ledger_reconciled = (
            decision.status == HITLStatus.APPROVED
            and ledger.resolve_uncertain("demo", "uncertain-call")
        )

        traces = TraceCollector(storage_path=str(trace_path))
        root = traces.start_trace("resume_showcase", trace_id="resume-demo")
        for name, result in (
            ("initial_execution", initial),
            ("restart_replay", replay),
            ("uncertain_execution", uncertain),
            ("uncertain_retry_blocked", blocked),
        ):
            span = traces.add_span(root, "tool_call", name)
            traces.end_span(
                span,
                output={"error": result["error"], "code": result.get("code")},
                error=(
                    str(result.get("content") or result.get("code") or "tool call failed")
                    if result["error"]
                    else None
                ),
            )
        review = traces.add_span(root, "workflow", "hitl_reconciliation")
        traces.end_span(review, output={"status": decision.status.value})
        traces.end_span(root, tokens_in=12, tokens_out=4)

        eval_report = await run_offline_eval(workspace / "offline-eval.json")
        checks = {
            "initial_execution_succeeded": initial["error"] is False,
            "restart_replayed_result": replay.get("replayed") is True,
            "completed_side_effect_not_duplicated": execution_count == 2,
            "uncertain_execution_blocked": blocked.get("code") == "tool_execution_uncertain",
            "hitl_reconciled": ledger_reconciled,
            "trace_persisted": TraceCollector(storage_path=str(trace_path)).get_trace("resume-demo")
            is not None,
            "offline_eval_passed": eval_report.get("pass_rate") == 1.0,
        }
        report = {
            "schema_version": 1,
            "scenario": "interruption-restart-ledger-hitl-trace-eval",
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "network_required": False,
                "api_key_required": False,
            },
            "passed": all(checks.values()),
            "checks": checks,
            "execution_count": execution_count,
            "audit_events": audit_events,
            "trace": traces.list_traces()[0],
            "eval": {
                "suite": eval_report.get("suite"),
                "pass_rate": eval_report.get("pass_rate"),
                "metrics": eval_report.get("metrics"),
                "regression": eval_report.get("regression"),
            },
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "data" / "release" / "resume-demo.json"
    )
    report = asyncio.run(run(parser.parse_args().output))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
