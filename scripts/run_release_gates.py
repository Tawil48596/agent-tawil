"""Run reproducible v2 release gates and write a machine-readable summary."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from shared.release_checks import scan_tracked_files
from shared.version import APP_VERSION

ROOT = Path(__file__).resolve().parents[1]


def remove_tree(path: Path) -> None:
    def make_writable_and_retry(function, target, _error) -> None:
        os.chmod(target, stat.S_IWRITE)
        function(target)

    shutil.rmtree(path, onerror=make_writable_and_retry)


def run_command(name: str, command: list[str], budget: float, cwd: Path = ROOT) -> dict:
    started = time.perf_counter()
    completed = subprocess.run(command, cwd=cwd, check=False)
    duration = round(time.perf_counter() - started, 3)
    passed = completed.returncode == 0 and duration <= budget
    return {
        "name": name,
        "passed": passed,
        "exit_code": completed.returncode,
        "duration_seconds": duration,
        "budget_seconds": budget,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/release/evidence.json")
    args = parser.parse_args()
    python = sys.executable
    npm = shutil.which("npm") or "npm"
    scratch = ROOT / "data/release/gate-tmp"
    if scratch.exists():
        remove_tree(scratch)
    (scratch / "source/traces").mkdir(parents=True)
    (scratch / "source/traces/history.json").write_text("{}", encoding="utf-8")

    findings = scan_tracked_files(ROOT)
    gates = [{"name": "tracked_secret_scan", "passed": not findings, "findings": findings}]
    commands = [
        (
            "python_tests",
            [
                python,
                "-m",
                "pytest",
                "-q",
                "--cov-fail-under=35",
                f"--cov-report=json:{scratch / 'coverage.json'}",
                "--basetemp",
                str(scratch / "pytest"),
            ],
            300,
            ROOT,
        ),
        (
            "critical_module_coverage",
            [
                python,
                "-m",
                "scripts.check_coverage_thresholds",
                str(scratch / "coverage.json"),
                "--minimum",
                "plugins/agent_engine/engine.py=85",
                "--minimum",
                "plugins/agent_engine/tool_dispatch.py=80",
                "--minimum",
                "plugins/checkpoint/execution_ledger.py=70",
                "--minimum",
                "plugins/conversation/session_store.py=80",
            ],
            15,
            ROOT,
        ),
        (
            "offline_agent",
            [python, "-m", "scripts.run_offline_eval", "--history", str(scratch / "eval.json")],
            15,
            ROOT,
        ),
        (
            "resume_showcase",
            [
                python,
                "-m",
                "scripts.run_resume_demo",
                "--output",
                str(scratch / "resume-demo.json"),
            ],
            20,
            ROOT,
        ),
        (
            "fault_drills",
            [
                python,
                "-m",
                "scripts.run_fault_drills",
                "--basetemp",
                str(scratch / "fault-pytest"),
            ],
            120,
            ROOT,
        ),
        (
            "backup_create",
            [
                python,
                "-m",
                "scripts.backup_data",
                "--create",
                str(scratch / "backup.zip"),
                "--data-root",
                str(scratch / "source"),
            ],
            15,
            ROOT,
        ),
        (
            "backup_verify",
            [python, "-m", "scripts.backup_data", "--verify", str(scratch / "backup.zip")],
            15,
            ROOT,
        ),
        (
            "backup_restore",
            [
                python,
                "-m",
                "scripts.backup_data",
                "--restore",
                str(scratch / "backup.zip"),
                "--data-root",
                str(scratch / "restored"),
            ],
            15,
            ROOT,
        ),
        ("web_lint", [npm, "run", "lint"], 60, ROOT / "web"),
        ("web_tests", [npm, "test"], 120, ROOT / "web"),
        ("web_build", [npm, "run", "build"], 180, ROOT / "web"),
    ]
    for name, command, budget, cwd in commands:
        gates.append(run_command(name, command, budget, cwd))

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    evidence = {
        "schema_version": 1,
        "version": APP_VERSION,
        "commit": commit,
        "created_at": datetime.now(UTC).isoformat(),
        "passed": all(gate["passed"] for gate in gates),
        "gates": gates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    remove_tree(scratch)
    print(json.dumps({"passed": evidence["passed"], "output": str(args.output)}))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
