"""向量库抽象层"""

import contextlib
import json
from pathlib import Path

import structlog

logger = structlog.get_logger()


class VectorStore:
    """向量存储抽象 — 支持 ChromaDB / Builtin"""

    def __init__(self, config: dict = None):
        cfg = config or {}
        vs_cfg = cfg.get("vector_store", {}) if isinstance(cfg, dict) else {}
        self._backend = vs_cfg.get("backend", "builtin")
        self._client = None
        self._collections: dict[str, BuiltinCollection] = {}  # builtin fallback
        self._storage_path = Path(vs_cfg.get("builtin", {}).get("path", "data/rag_vectors.json"))

        if self._backend == "chromadb":
            try:
                import chromadb

                chroma_cfg = vs_cfg.get("chromadb", {})
                self._client = chromadb.PersistentClient(
                    path=chroma_cfg.get("path", "./chroma_data"),
                )
            except ImportError:
                self._backend = "builtin"
        if self._backend == "builtin":
            self._load_builtin()

    def _load_builtin(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
            self._collections = {
                name: BuiltinCollection(name, documents) for name, documents in payload.items()
            }
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            self._collections = {}

    def _persist_builtin(self) -> None:
        if self._backend != "builtin":
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {name: collection.documents() for name, collection in self._collections.items()}
        temporary = self._storage_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self._storage_path)

    async def add(self, collection: str, chunks: list[dict]):
        """添加 chunks 到向量库"""
        if self._client and self._backend == "chromadb":
            col = self._client.get_or_create_collection(name=collection)
            ids = [chunk.get("id") or f"{collection}_{i}" for i, chunk in enumerate(chunks)]
            documents = [c["content"] for c in chunks]
            metadatas = [self._normalize_metadata(c.get("metadata", {})) for c in chunks]
            col.upsert(ids=ids, documents=documents, metadatas=metadatas)
        else:
            if collection not in self._collections:
                self._collections[collection] = BuiltinCollection(collection)
            self._collections[collection].add(chunks)
            self._persist_builtin()

    @staticmethod
    def _normalize_metadata(metadata: dict) -> dict:
        normalized = {}
        for key, value in metadata.items():
            if value is None:
                normalized[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                normalized[key] = value
            else:
                normalized[key] = json.dumps(value, ensure_ascii=False)
        return normalized

    async def search(
        self, query: str, collections: list[str] = None, top_k: int = 10
    ) -> list[dict]:
        """搜索"""
        all_results = []

        if collections:
            search_collections = collections
        elif self._client and self._backend == "chromadb":
            search_collections = [
                collection.name
                for collection in self._client.list_collections()
                if collection.name.startswith("kb_")
            ]
        else:
            search_collections = list(self._collections.keys())

        if self._client and self._backend == "chromadb":
            for col_name in search_collections:
                try:
                    col = self._client.get_collection(name=col_name)
                    results = col.query(query_texts=[query], n_results=top_k)
                    if results["ids"] and results["ids"][0]:
                        for i, mid in enumerate(results["ids"][0]):
                            all_results.append(
                                {
                                    "id": mid,
                                    "content": results["documents"][0][i]
                                    if results["documents"]
                                    else "",
                                    "score": 1.0 - results["distances"][0][i]
                                    if results.get("distances")
                                    else 0.5,
                                    "metadata": results["metadatas"][0][i]
                                    if results["metadatas"]
                                    else {},
                                }
                            )
                except Exception:
                    pass
        else:
            for col_name in search_collections:
                if col_name in self._collections:
                    results = self._collections[col_name].search(query, top_k)
                    all_results.extend(results)

        return all_results[:top_k]

    async def delete_collection(self, collection: str):
        if self._client and self._backend == "chromadb":
            with contextlib.suppress(Exception):
                self._client.delete_collection(name=collection)
        self._collections.pop(collection, None)
        self._persist_builtin()

    async def delete_document(self, collection: str, document_id: str) -> None:
        if self._client and self._backend == "chromadb":
            try:
                col = self._client.get_collection(name=collection)
                col.delete(where={"document_id": document_id})
            except Exception:
                pass
        elif collection in self._collections:
            self._collections[collection].delete_document(document_id)
            self._persist_builtin()

    async def list_documents(self, collection: str) -> list[dict]:
        if self._client and self._backend == "chromadb":
            try:
                col = self._client.get_collection(name=collection)
                result = col.get(include=["documents", "metadatas"])
                return [
                    {
                        "id": result["ids"][index],
                        "content": result["documents"][index],
                        "metadata": result["metadatas"][index] or {},
                    }
                    for index in range(len(result["ids"]))
                ]
            except Exception:
                return []
        target = self._collections.get(collection)
        return target.documents() if target else []


class BuiltinCollection:
    """内置向量存储 — 关键词匹配 (零依赖)"""

    def __init__(self, name: str, documents: list[dict] | None = None):
        self.name = name
        self._docs: list[dict] = list(documents or [])

    def add(self, chunks: list[dict]):
        self._docs.extend(chunks)

    def documents(self) -> list[dict]:
        return [dict(document) for document in self._docs]

    def delete_document(self, document_id: str) -> None:
        self._docs = [
            document
            for document in self._docs
            if document.get("metadata", {}).get("document_id") != document_id
        ]

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        query_lower = query.lower()
        scored = []

        for i, doc in enumerate(self._docs):
            content = doc.get("content", "")
            score = 0.0
            content_lower = content.lower()

            if query_lower in content_lower:
                score = 0.9
            else:
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                overlap = query_words & content_words
                if overlap:
                    score = 0.5 * len(overlap) / max(len(query_words), 1)

            if score > 0:
                scored.append(
                    {
                        "id": doc.get("id") or f"{self.name}_{i}",
                        "content": content,
                        "score": score,
                        "metadata": doc.get("metadata", {}),
                    }
                )

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
