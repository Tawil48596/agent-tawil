"""长期记忆 — ChromaDB / 内置 SQLite 向量存储 + 记忆衰减"""

import json
import math
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class MemoryEntry:
    id: str
    content: str
    embedding: Optional[list[float]] = None
    type: str = "fact"          # fact | preference | event | lesson
    importance: float = 0.5
    source_session: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[int] = None   # 过期时间 (秒)


class LongTermMemory:
    """长期记忆存储

    支持后端:
      - builtin: SQLite + 余弦相似度 (零依赖)
      - chromadb: ChromaDB 向量检索
    """

    def __init__(self, config: dict = None):
        cfg = config or {}
        mem_cfg = cfg.get("memory", {}) if isinstance(cfg, dict) else {}
        self._backend = mem_cfg.get("long_term_backend", "builtin")
        self._importance_threshold = mem_cfg.get("importance_threshold", 0.3)
        self._decay_lambda = mem_cfg.get("decay_lambda", 0.01)
        self._max_retrieved = mem_cfg.get("max_retrieved", 10)

        self._storage: dict[str, MemoryEntry] = {}
        self._chroma_client = None
        self._chroma_collection = None

        if self._backend == "chromadb":
            self._init_chromadb(cfg)

    def _init_chromadb(self, config: dict):
        try:
            import chromadb
            chroma_cfg = config.get("vector_store", {}).get("chromadb", {})
            path = chroma_cfg.get("path", "./chroma_data")
            self._chroma_client = chromadb.PersistentClient(path=path)
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name="long_term_memory",
                metadata={"hnsw:space": "cosine"},
            )
        except ImportError:
            self._backend = "builtin"

    # ── CRUD ──

    async def save(self, entry: MemoryEntry) -> str:
        """保存记忆条目"""
        if entry.importance < self._importance_threshold:
            return ""  # 低于阈值，不保存
        if not entry.id:
            import uuid
            entry.id = uuid.uuid4().hex[:12]

        if self._backend == "chromadb" and self._chroma_collection:
            self._chroma_collection.upsert(
                ids=[entry.id],
                documents=[entry.content],
                metadatas=[{
                    "type": entry.type,
                    "importance": entry.importance,
                    "source_session": entry.source_session or "",
                    "created_at": entry.created_at,
                }],
            )

        self._storage[entry.id] = entry
        return entry.id

    async def batch_save(self, entries: list[MemoryEntry]) -> list[str]:
        """批量保存"""
        ids = []
        for entry in entries:
            eid = await self.save(entry)
            if eid:
                ids.append(eid)
        return ids

    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        entry = self._storage.get(entry_id)
        if entry:
            entry.last_accessed_at = time.time()
            entry.access_count += 1
        return entry

    async def delete(self, entry_id: str) -> bool:
        if entry_id in self._storage:
            del self._storage[entry_id]
        if self._chroma_collection:
            try:
                self._chroma_collection.delete(ids=[entry_id])
            except Exception:
                pass
        return True

    async def clear(self):
        self._storage.clear()
        if self._chroma_collection:
            try:
                # ChromaDB 不支持 clear，删除并重建
                self._chroma_client.delete_collection("long_term_memory")
                self._chroma_collection = self._chroma_client.create_collection(
                    name="long_term_memory",
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                pass

    # ── 检索 ──

    async def search(self, query: str, limit: int = None,
                      memory_type: str = None) -> list[MemoryEntry]:
        """搜索记忆"""
        limit = limit or self._max_retrieved

        if self._backend == "chromadb" and self._chroma_collection:
            return await self._search_chromadb(query, limit, memory_type)
        else:
            return await self._search_builtin(query, limit, memory_type)

    async def _search_chromadb(self, query: str, limit: int,
                                memory_type: str = None) -> list[MemoryEntry]:
        where = None
        if memory_type:
            where = {"type": memory_type}

        results = self._chroma_collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,
        )

        entries = []
        if results["ids"] and results["ids"][0]:
            for i, mid in enumerate(results["ids"][0]):
                entry = self._storage.get(mid)
                if not entry:
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    entry = MemoryEntry(
                        id=mid,
                        content=results["documents"][0][i] if results["documents"] else "",
                        type=meta.get("type", "fact"),
                        importance=meta.get("importance", 0.5),
                    )
                    self._storage[mid] = entry
                entries.append(entry)

        return self._apply_decay(entries)

    async def _search_builtin(self, query: str, limit: int,
                               memory_type: str = None) -> list[MemoryEntry]:
        """内置关键词匹配 + 时间衰减"""
        query_lower = query.lower()
        scored = []

        for entry in self._storage.values():
            if memory_type and entry.type != memory_type:
                continue

            # 简单关键词匹配得分
            content_lower = entry.content.lower()
            score = 0.0
            if query_lower in content_lower:
                score = 0.8
            else:
                # 词级别匹配
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                overlap = query_words & content_words
                if overlap:
                    score = 0.4 * (len(overlap) / max(len(query_words), 1))

            if score > 0:
                scored.append((entry, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        entries = [e for e, _ in scored[:limit]]
        return self._apply_decay(entries)

    # ── 记忆衰减 ──

    def _apply_decay(self, entries: list[MemoryEntry]) -> list[MemoryEntry]:
        """应用时间衰减公式: importance_effective = importance * e^(-λ * days)"""
        now = time.time()
        for entry in entries:
            days_since_access = (now - entry.last_accessed_at) / 86400.0
            decay_factor = math.exp(-self._decay_lambda * days_since_access)
            entry.importance *= decay_factor
            entry.access_count += 1
            entry.last_accessed_at = now

        # 删除衰减到阈值以下的
        to_delete = [
            eid for eid, e in self._storage.items()
            if e.importance < self._importance_threshold * 0.5
        ]
        for eid in to_delete:
            del self._storage[eid]

        return entries

    # ── 统计 ──

    @property
    def count(self) -> int:
        return len(self._storage)

    def stats(self) -> dict:
        types = {}
        for e in self._storage.values():
            types[e.type] = types.get(e.type, 0) + 1
        return {
            "total": len(self._storage),
            "by_type": types,
            "backend": self._backend,
        }
