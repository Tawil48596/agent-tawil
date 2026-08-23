"""Atomic, versioned JSON collection storage with legacy-list compatibility."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


class UnsupportedSchemaVersion(ValueError):  # noqa: N818  # public compatibility name
    pass


def load_collection(path: str | Path, current_version: int = 1) -> list[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        return []
    payload = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        raise ValueError("Versioned store root must be an object")
    version = int(payload.get("schema_version", 0))
    if version > current_version:
        raise UnsupportedSchemaVersion(
            f"Schema version {version} is newer than supported {current_version}"
        )
    if version < 1 or not isinstance(payload.get("items"), list):
        raise ValueError("Invalid versioned store envelope")
    return [item for item in payload["items"] if isinstance(item, dict)]


def write_collection(
    path: str | Path, items: list[dict[str, Any]], schema_version: int = 1
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(
                {"schema_version": schema_version, "items": items},
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
