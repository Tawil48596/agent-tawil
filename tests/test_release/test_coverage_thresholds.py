from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_cli_fails_when_module_is_below_threshold(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(
        json.dumps(
            {"files": {"plugins/agent_engine/engine.py": {"summary": {"percent_covered": 79.5}}}}
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.check_coverage_thresholds",
            str(report),
            "--minimum",
            "plugins/agent_engine/engine.py=80",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert json.loads(result.stdout) == {
        "passed": False,
        "modules": [
            {
                "path": "plugins/agent_engine/engine.py",
                "actual": 79.5,
                "required": 80.0,
                "passed": False,
            }
        ],
    }


def test_cli_fails_when_required_module_is_missing(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps({"files": {}}), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.check_coverage_thresholds",
            str(report),
            "--minimum",
            "plugins/checkpoint/execution_ledger.py=70",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert json.loads(result.stdout) == {
        "passed": False,
        "modules": [
            {
                "path": "plugins/checkpoint/execution_ledger.py",
                "actual": None,
                "required": 70.0,
                "passed": False,
            }
        ],
    }


def test_cli_normalizes_windows_report_paths(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(
        json.dumps(
            {
                "files": {
                    "plugins\\conversation\\session_store.py": {
                        "summary": {"percent_covered": 85.25}
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.check_coverage_thresholds",
            str(report),
            "--minimum",
            "plugins/conversation/session_store.py=80",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "passed": True,
        "modules": [
            {
                "path": "plugins/conversation/session_store.py",
                "actual": 85.25,
                "required": 80.0,
                "passed": True,
            }
        ],
    }
