"""ChromaDB 记忆后端"""


class ChromaMemoryBackend:
    """ChromaDB 向量记忆存储"""

    def __init__(self, path: str = "./chroma_data", collection_name: str = "memory"):
        self._client = None
        self._collection = None
        try:
            import chromadb

            self._client = chromadb.PersistentClient(path=path)
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except ImportError:
            pass

    async def save(self, entry: dict) -> str:
        eid = entry.get("id", "")
        if self._collection:
            self._collection.upsert(
                ids=[eid],
                documents=[entry.get("content", "")],
                metadatas=[{k: v for k, v in entry.items() if k not in ("content", "embedding")}],
            )
        return eid

    async def search(self, query: str, limit: int = 10, **filters) -> list[dict]:
        if not self._collection:
            return []
        results = self._collection.query(
            query_texts=[query], n_results=limit, where=filters if filters else None
        )
        entries = []
        if results["ids"] and results["ids"][0]:
            for i, mid in enumerate(results["ids"][0]):
                entries.append(
                    {
                        "id": mid,
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    }
                )
        return entries

    async def get(self, entry_id: str) -> dict | None:
        if self._collection:
            r = self._collection.get(ids=[entry_id])
            if r["ids"]:
                return {
                    "id": r["ids"][0],
                    "content": r["documents"][0] if r["documents"] else "",
                    "metadata": r["metadatas"][0] if r["metadatas"] else {},
                }
        return None

    async def delete(self, entry_id: str) -> bool:
        if self._collection:
            self._collection.delete(ids=[entry_id])
        return True

    async def clear(self) -> None:
        if self._collection and self._client:
            self._client.delete_collection(self._collection.name)
            self._collection = self._client.create_collection(name=self._collection.name)
