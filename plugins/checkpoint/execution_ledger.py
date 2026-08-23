"""Durable completed-tool-call ledger used for idempotent retries."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


class ToolExecutionLedger:
    """Persist successful tool results by session and model tool-call id."""

    def __init__(
        self, path: str | Path = "data/tool_executions", lease_seconds: float = 60.0
    ) -> None:
        self._path = Path(path)
        self._path.mkdir(parents=True, exist_ok=True)
        self._lease_seconds = max(0.0, float(lease_seconds))

    @staticmethod
    def _digest(session_id: str, call_id: str) -> str:
        value = f"{session_id}\0{call_id}".encode("utf-8")
        return hashlib.sha256(value).hexdigest()

    def _entry_path(self, session_id: str, call_id: str) -> Path:
        return self._path / f"{self._digest(session_id, call_id)}.json"

    def _write(self, destination: Path, payload: dict[str, Any]) -> None:
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8"
            )
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

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

    def acquire(
        self, session_id: str, call_id: str, tool: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Claim a call or return its durable replay/recovery decision."""
        if not session_id or not call_id:
            return {"action": "execute", "attempt_id": ""}
        path = self._entry_path(session_id, call_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            payload = None
        except (OSError, json.JSONDecodeError):
            return {"action": "uncertain", "reason": "corrupt_record"}

        arguments_digest = self._arguments_digest(arguments)
        if payload is not None:
            if (
                payload.get("tool") != tool
                or payload.get("arguments_digest") != arguments_digest
            ):
                return {"action": "conflict"}
            status = payload.get("status", "completed" if "result" in payload else "uncertain")
            if status == "completed" and isinstance(payload.get("result"), dict):
                return {"action": "replay", "result": dict(payload["result"])}
            if status == "running":
                if float(payload.get("lease_expires_at", 0)) > time.time():
                    return {"action": "busy"}
                payload.update(status="uncertain", reason="lease_expired")
                self._write(path, payload)
            return {"action": "uncertain", "reason": payload.get("reason", status)}

        attempt_id = uuid.uuid4().hex
        self._write(path, {
            "status": "running",
            "tool": tool,
            "arguments_digest": arguments_digest,
            "attempt_id": attempt_id,
            "lease_expires_at": time.time() + self._lease_seconds,
        })
        return {"action": "execute", "attempt_id": attempt_id}

    def release(self, session_id: str, call_id: str, attempt_id: str) -> None:
        """Release a failed attempt so an explicit retry may execute."""
        if not session_id or not call_id or not attempt_id:
            return
        path = self._entry_path(session_id, call_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return
        if payload.get("status") == "running" and payload.get("attempt_id") == attempt_id:
            path.unlink(missing_ok=True)

    def mark_uncertain(
        self, session_id: str, call_id: str, attempt_id: str, reason: str
    ) -> None:
        """Fail closed when execution may have produced an external side effect."""
        if not session_id or not call_id or not attempt_id:
            return
        path = self._entry_path(session_id, call_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return
        if payload.get("status") == "running" and payload.get("attempt_id") == attempt_id:
            payload.update(status="uncertain", reason=reason, lease_expires_at=0)
            self._write(path, payload)

    def resolve_uncertain(self, session_id: str, call_id: str) -> bool:
        """Explicitly clear an uncertain call after external reconciliation."""
        path = self._entry_path(session_id, call_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return False
        if payload.get("status") != "uncertain":
            return False
        path.unlink(missing_ok=True)
        return True

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
        payload = {
            "status": "completed",
            "tool": tool,
            "arguments_digest": self._arguments_digest(arguments),
            "result": result,
        }
        self._write(destination, payload)
