"""Local data backup archives with a versioned, hash-verified manifest."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ARCHIVE_SCHEMA_VERSION = 1


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe_member(name: str) -> PurePosixPath:
    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts or member.parts[:1] != ("data",):
        raise ValueError(f"Unsafe backup member: {name}")
    return member


def create_backup(data_root: str | Path, archive_path: str | Path) -> dict:
    root = Path(data_root).resolve()
    archive = Path(archive_path)
    archive.parent.mkdir(parents=True, exist_ok=True)
    files: list[dict] = []
    temporary = archive.with_name(f".{archive.name}.{uuid.uuid4().hex}.tmp")
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as bundle:
            if root.exists():
                for source in sorted(path for path in root.rglob("*") if path.is_file()):
                    relative = source.relative_to(root).as_posix()
                    content = source.read_bytes()
                    name = f"data/{relative}"
                    bundle.writestr(name, content)
                    files.append({"path": name, "size": len(content), "sha256": _digest(content)})
            manifest = {
                "schema_version": ARCHIVE_SCHEMA_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "files": files,
            }
            bundle.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        os.replace(temporary, archive)
        return manifest
    finally:
        temporary.unlink(missing_ok=True)


def verify_backup(archive_path: str | Path) -> dict:
    with zipfile.ZipFile(archive_path, "r") as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        version = int(manifest.get("schema_version", 0))
        if version > ARCHIVE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported backup schema version: {version}")
        if version < 1 or not isinstance(manifest.get("files"), list):
            raise ValueError("Invalid backup manifest")
        for item in manifest["files"]:
            member = _safe_member(item["path"])
            content = bundle.read(member.as_posix())
            if len(content) != item["size"] or _digest(content) != item["sha256"]:
                raise ValueError(f"Backup integrity check failed: {member}")
        return manifest


def restore_backup(archive_path: str | Path, data_root: str | Path) -> dict:
    manifest = verify_backup(archive_path)
    root = Path(data_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as bundle:
        for item in manifest["files"]:
            relative = Path(*_safe_member(item["path"]).parts[1:])
            destination = (root / relative).resolve()
            if root not in destination.parents:
                raise ValueError(f"Restore target escaped data root: {relative}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f".{destination.name}.restore.tmp")
            temporary.write_bytes(bundle.read(item["path"]))
            os.replace(temporary, destination)
    return manifest
