"""Mem0 记忆后端 — Mem0 SaaS 集成"""

from typing import Optional


class Mem0MemoryBackend:
    """Mem0 云端记忆后端"""

    def __init__(self, api_key: str = ""):
        self._api_key = api_key

    @property
    def is_available(self) -> bool: return bool(self._api_key)

    async def save(self, entry: dict) -> str: return entry.get("id", "")
    async def search(self, query: str, limit: int = 10, **filters) -> list[dict]: return []
    async def get(self, entry_id: str) -> Optional[dict]: return None
    async def delete(self, entry_id: str) -> bool: return True
    async def clear(self) -> None: pass
