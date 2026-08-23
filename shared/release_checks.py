"""Release-time checks that never expose matched credential values."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai_key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "anthropic_key": re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
    "github_token": re.compile(r"\b(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
}


def scan_text(text: str) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for kind, pattern in SECRET_PATTERNS.items():
            if pattern.search(line):
                findings.append((line_number, kind))
    return findings


def scan_tracked_files(root: str | Path) -> list[dict]:
    repository = Path(root)
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=repository, check=True, capture_output=True
    ).stdout.decode("utf-8").split("\0")
    findings: list[dict] = []
    for relative in filter(None, listed):
        path = repository / relative
        content = path.read_bytes()
        if b"\0" in content:
            continue
        for line, kind in scan_text(content.decode("utf-8", errors="ignore")):
            findings.append({"path": relative, "line": line, "kind": kind})
    return findings
