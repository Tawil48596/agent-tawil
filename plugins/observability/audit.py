"""Append-only, redacted audit events for security-sensitive runtime actions."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_SENSITIVE_PARTS = (
    "api_key", "apikey", "authorization", "cookie",
    "credential", "password", "secret", "token",
)


def redact_sensitive(value: Any) -> Any:
    """Return a JSON-safe copy with credential-like fields removed."""
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if any(part in str(key).lower() for part in _SENSITIVE_PARTS)
                else redact_sensitive(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


class AuditLog:
    """Persist one redacted JSON object per line without blocking the caller."""

    def __init__(self, config: dict | None = None):
        cfg = config or {}
        self.enabled = bool(cfg.get("enabled", True))
        self.path = Path(cfg.get("path", "data/audit/events.jsonl"))
        self._lock = threading.Lock()

    def record(self, event_type: str, **fields: Any) -> bool:
        if not self.enabled:
            return False
        event = {
            "event_id": uuid.uuid4().hex,
            "event_type": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            **redact_sensitive(fields),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
            with self._lock, self.path.open("a", encoding="utf-8") as stream:
                stream.write(f"{line}\n")
            return True
        except OSError:
            return False
