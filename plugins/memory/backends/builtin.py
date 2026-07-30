"""内置记忆后端 — SQLite + JSON (零依赖)"""

import json
import os
import time
from pathlib import Path
from typing import Optional


class BuiltinMemoryBackend:
    """内置记忆存储 — SQLite + 文件持久化"""

    def __init__(self, data_dir: str = "data/memory"):
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict] = {}
        self._load()

    async def save(self, entry: dict) -> str:
        eid = entry.get("id", "")
        self._cache[eid] = entry
        self._persist(eid, entry)
        return eid

    async def search(self, query: str, limit: int = 10, **filters) -> list[dict]:
        q = query.lower()
        results = []
        for e in self._cache.values():
            content = e.get("content", "").lower()
            if q in content:
                results.append(e)
        return results[:limit]

    async def get(self, entry_id: str) -> Optional[dict]:
        return self._cache.get(entry_id)

    async def delete(self, entry_id: str) -> bool:
        if entry_id in self._cache:
            del self._cache[entry_id]
            (self._dir / f"{entry_id}.json").unlink(missing_ok=True)
            return True
        return False

    async def clear(self) -> None:
        self._cache.clear()
        for f in self._dir.glob("*.json"):
            f.unlink()

    def _persist(self, eid: str, entry: dict) -> None:
        (self._dir / f"{eid}.json").write_text(
            json.dumps(entry, ensure_ascii=False, default=str)
        )

    def _load(self) -> None:
        for f in self._dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                self._cache[data.get("id", f.stem)] = data
            except Exception:
                pass
