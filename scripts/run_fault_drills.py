"""Run deterministic crash, timeout, recovery and regression drills."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DRILLS = [
    "tests/test_checkpoint_store.py",
    "tests/test_tools/test_tool_dispatch.py",
    "tests/test_evals/test_fake_llm.py",
    "tests/test_resilience/test_resilience_manager.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basetemp", type=Path)
    args = parser.parse_args()
    command = [sys.executable, "-m", "pytest", "-q", "--no-cov"]
    if args.basetemp:
        command.extend(["--basetemp", str(args.basetemp)])
    command.extend(DRILLS)
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        print("Fault drills failed")
        return completed.returncode
    print("Fault drills passed: checkpoint, lease, timeout, eval and fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
