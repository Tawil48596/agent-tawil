"""Enforce per-module coverage thresholds from a coverage.py JSON report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def normalize_module_path(value: str) -> str:
    return value.replace("\\", "/").removeprefix("./")


def parse_minimum(value: str) -> tuple[str, float]:
    module, separator, raw_percent = value.rpartition("=")
    if not separator or not module:
        raise argparse.ArgumentTypeError("expected MODULE=PERCENT")
    try:
        percent = float(raw_percent)
    except ValueError as error:
        raise argparse.ArgumentTypeError("PERCENT must be numeric") from error
    if not 0 <= percent <= 100:
        raise argparse.ArgumentTypeError("PERCENT must be between 0 and 100")
    return normalize_module_path(module), percent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--minimum", action="append", required=True, type=parse_minimum)
    args = parser.parse_args()

    coverage = json.loads(args.report.read_text(encoding="utf-8"))
    files = {
        normalize_module_path(module): details for module, details in coverage["files"].items()
    }
    modules = []
    for module, required in args.minimum:
        file_coverage = files.get(module)
        actual = (
            float(file_coverage["summary"]["percent_covered"])
            if file_coverage is not None
            else None
        )
        modules.append(
            {
                "path": module,
                "actual": actual,
                "required": required,
                "passed": actual is not None and actual >= required,
            }
        )

    result = {"passed": all(module["passed"] for module in modules), "modules": modules}
    print(json.dumps(result, separators=(",", ":")))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
