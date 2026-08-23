"""Verified, isolated tool package storage and rollback."""

import hashlib
import hmac
import io
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class PackageManifest:
    name: str
    version: str
    sha256: str
    signature: str = ""


class ToolPackageStore:
    _SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

    def __init__(self, root: str | Path = "data/tool_packages", trusted_key: str = ""):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._state_path = self.root / "installed.json"
        self._trusted_key = trusted_key.encode("utf-8")
        self._state = self._load_state()

    def _load_state(self) -> dict:
        if not self._state_path.exists():
            return {}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        temp = self._state_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        temp.replace(self._state_path)

    def verify(self, artifact: bytes, manifest: PackageManifest) -> None:
        if not self._SAFE_ID.fullmatch(manifest.name):
            raise ValueError("Package name is invalid")
        if not self._SAFE_ID.fullmatch(manifest.version) or ".." in manifest.version:
            raise ValueError("Package version is invalid")
        digest = hashlib.sha256(artifact).hexdigest()
        if not hmac.compare_digest(digest, manifest.sha256.lower()):
            raise ValueError("Package checksum mismatch")
        if self._trusted_key:
            if not manifest.signature:
                raise ValueError("Package signature is required")
            expected = hmac.new(
                self._trusted_key, digest.encode("ascii"), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected, manifest.signature.lower()):
                raise ValueError("Package signature is invalid")

    @staticmethod
    def _safe_members(archive: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, PurePosixPath]]:
        members = []
        for member in archive.infolist():
            normalized = member.filename.replace("\\", "/")
            path = PurePosixPath(normalized)
            if (
                path.is_absolute()
                or ".." in path.parts
                or member.filename.startswith(("/", "\\"))
                or any(":" in part for part in path.parts)
            ):
                raise ValueError("Package contains an unsafe path")
            if member.is_dir() or not member.filename.endswith((".py", ".json", ".md", ".txt")):
                continue
            members.append((member, path))
        return members

    def install(self, artifact: bytes, manifest: PackageManifest) -> dict:
        self.verify(artifact, manifest)
        target = self.root / manifest.name / manifest.version
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(artifact)) as archive:
            for member, relative_path in self._safe_members(archive):
                destination = target.joinpath(*relative_path.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(member))
        record = self._state.setdefault(manifest.name, {"active": None, "versions": []})
        previous = record.get("active")
        if manifest.version not in record["versions"]:
            record["versions"].append(manifest.version)
        record["previous"] = previous
        record["active"] = manifest.version
        self._save()
        return {
            "ok": True,
            "name": manifest.name,
            "version": manifest.version,
            "previous": previous,
            "path": str(target),
        }

    def rollback(self, name: str, version: str | None = None) -> dict:
        record = self._state.get(name)
        if not record:
            raise ValueError(f"Tool package not installed: {name}")
        target = version or record.get("previous")
        if not target or target not in record.get("versions", []):
            raise ValueError("No rollback version is available")
        current = record.get("active")
        record["active"] = target
        record["previous"] = current
        self._save()
        return {"ok": True, "name": name, "version": target, "previous": current}

    def status(self, name: str = "") -> dict:
        return self._state.get(name, {}) if name else dict(self._state)
