"""Durable completed-tool-call ledger used for idempotent retries."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any


class ToolExecutionLedger:
    """Persist successful tool results by session and model tool-call id."""

    def __init__(self, path: str | Path = "data/tool_executions") -> None:
        self._path = Path(path)
        self._path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _digest(session_id: str, call_id: str) -> str:
        value = f"{session_id}\0{call_id}".encode("utf-8")
        return hashlib.sha256(value).hexdigest()

    def _entry_path(self, session_id: str, call_id: str) -> Path:
        return self._path / f"{self._digest(session_id, call_id)}.json"

    @staticmethod
    def _arguments_digest(arguments: dict[str, Any]) -> str:
        encoded = json.dumps(arguments, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def load(
        self, session_id: str, call_id: str, tool: str, arguments: dict[str, Any]
    ) -> dict[str, Any] | None:
        if not session_id or not call_id:
            return None
        try:
            payload = json.loads(
                self._entry_path(session_id, call_id).read_text(encoding="utf-8")
            )
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        result = payload.get("result")
        if (
            payload.get("tool") != tool
            or payload.get("arguments_digest") != self._arguments_digest(arguments)
            or not isinstance(result, dict)
        ):
            return None
        if result.get("error"):
            return None
        return dict(result)

    def store(
        self,
        session_id: str,
        call_id: str,
        tool: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        if not session_id or not call_id or result.get("error"):
            return
        destination = self._entry_path(session_id, call_id)
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        payload = {
            "tool": tool,
            "arguments_digest": self._arguments_digest(arguments),
            "result": result,
        }
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8"
            )
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
