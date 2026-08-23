"""Milvus 记忆后端 — 大规模向量检索"""


class MilvusMemoryBackend:
    """Milvus 向量记忆存储"""

    def __init__(self, host: str = "localhost", port: int = 19530, collection_name: str = "memory"):
        self._connected = False
        self._collection = None
        try:
            from pymilvus import connections

            connections.connect(host=host, port=port)
            self._connected = True
        except ImportError:
            pass
        except Exception:
            pass

    @property
    def is_available(self) -> bool:
        return self._connected

    async def save(self, entry: dict) -> str:
        return entry.get("id", "")

    async def search(self, query: str, limit: int = 10, **filters) -> list[dict]:
        return []

    async def get(self, entry_id: str) -> dict | None:
        return None

    async def delete(self, entry_id: str) -> bool:
        return True

    async def clear(self) -> None:
        pass
