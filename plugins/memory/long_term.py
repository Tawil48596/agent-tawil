"""长期记忆 — ChromaDB / 内置 SQLite 向量存储 + 记忆衰减"""

import json
import math
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class MemoryEntry:
    id: str
    content: str
    embedding: Optional[list[float]] = None
    type: str = "fact"          # fact | preference | event | lesson
    importance: float = 0.5
    source_session: Optional[str] = None
    source: str = "manual"
    user_id: str = "local"
    project_id: str = "default"
    tags: list[str] = field(default_factory=list)
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
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
        self._storage_path = Path(mem_cfg.get("storage_path", "data/memory.json"))

        self._storage: dict[str, MemoryEntry] = {}
        self._chroma_client = None
        self._chroma_collection = None

        self._load_builtin()
        if self._backend == "chromadb":
            self._init_chromadb(cfg)

    def _load_builtin(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            entries = json.loads(self._storage_path.read_text(encoding="utf-8"))
            for data in entries:
                entry = MemoryEntry(**data)
                self._storage[entry.id] = entry
        except (OSError, TypeError, ValueError):
            self._storage = {}

    def _persist_builtin(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "id": entry.id,
                "content": entry.content,
                "embedding": entry.embedding,
                "type": entry.type,
                "importance": entry.importance,
                "source_session": entry.source_session,
                "source": entry.source,
                "user_id": entry.user_id,
                "project_id": entry.project_id,
                "tags": entry.tags,
                "confidence": entry.confidence,
                "created_at": entry.created_at,
                "updated_at": entry.updated_at,
                "last_accessed_at": entry.last_accessed_at,
                "access_count": entry.access_count,
                "ttl": entry.ttl,
            }
            for entry in self._storage.values()
        ]
        temporary = self._storage_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self._storage_path)

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
        normalized_content = " ".join(entry.content.strip().lower().split())
        for existing in self._storage.values():
            if (
                existing.user_id == entry.user_id
                and existing.project_id == entry.project_id
                and " ".join(existing.content.strip().lower().split()) == normalized_content
            ):
                existing.importance = max(existing.importance, entry.importance)
                existing.confidence = max(existing.confidence, entry.confidence)
                existing.updated_at = time.time()
                self._persist_builtin()
                return existing.id
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
                    "source": entry.source,
                    "user_id": entry.user_id,
                    "project_id": entry.project_id,
                    "tags": json.dumps(entry.tags, ensure_ascii=False),
                    "confidence": entry.confidence,
                    "created_at": entry.created_at,
                }],
            )

        self._storage[entry.id] = entry
        self._persist_builtin()
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
            self._persist_builtin()
        return entry

    async def delete(self, entry_id: str) -> bool:
        if entry_id in self._storage:
            del self._storage[entry_id]
        if self._chroma_collection:
            try:
                self._chroma_collection.delete(ids=[entry_id])
            except Exception:
                pass
        self._persist_builtin()
        return True

    async def update(self, entry_id: str, **changes: Any) -> Optional[MemoryEntry]:
        entry = self._storage.get(entry_id)
        if not entry:
            return None
        allowed = {
            "content", "type", "importance", "source_session", "source",
            "user_id", "project_id", "tags", "confidence", "ttl",
        }
        for key, value in changes.items():
            if key in allowed and value is not None:
                setattr(entry, key, value)
        entry.updated_at = time.time()
        await self.save(entry)
        return entry

    async def clear(self, user_id: str = None, project_id: str = None):
        if user_id is None and project_id is None:
            self._storage.clear()
        else:
            self._storage = {
                entry_id: entry
                for entry_id, entry in self._storage.items()
                if not (
                    (user_id is None or entry.user_id == user_id)
                    and (project_id is None or entry.project_id == project_id)
                )
            }
        self._persist_builtin()
        if self._chroma_collection:
            try:
                if user_id is None and project_id is None:
                    self._chroma_client.delete_collection("long_term_memory")
                    self._chroma_collection = self._chroma_client.create_collection(
                        name="long_term_memory",
                        metadata={"hnsw:space": "cosine"},
                    )
                else:
                    where = self._chroma_where(
                        None, user_id=user_id, project_id=project_id
                    )
                    self._chroma_collection.delete(where=where)
            except Exception:
                pass

    # ── 检索 ──

    async def search(
        self,
        query: str,
        limit: int = None,
        memory_type: str = None,
        user_id: str = None,
        project_id: str = None,
    ) -> list[MemoryEntry]:
        """搜索记忆"""
        limit = limit or self._max_retrieved

        if self._backend == "chromadb" and self._chroma_collection:
            return await self._search_chromadb(
                query, limit, memory_type, user_id, project_id
            )
        else:
            return await self._search_builtin(
                query, limit, memory_type, user_id, project_id
            )

    @staticmethod
    def _chroma_where(
        memory_type: str = None,
        *,
        user_id: str = None,
        project_id: str = None,
    ) -> Optional[dict]:
        filters = []
        if memory_type:
            filters.append({"type": memory_type})
        if user_id:
            filters.append({"user_id": user_id})
        if project_id:
            filters.append({"project_id": project_id})
        if not filters:
            return None
        return filters[0] if len(filters) == 1 else {"$and": filters}

    async def _search_chromadb(
        self,
        query: str,
        limit: int,
        memory_type: str = None,
        user_id: str = None,
        project_id: str = None,
    ) -> list[MemoryEntry]:
        where = self._chroma_where(
            memory_type, user_id=user_id, project_id=project_id
        )

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
                        source_session=meta.get("source_session") or None,
                        source=meta.get("source", "manual"),
                        user_id=meta.get("user_id", "local"),
                        project_id=meta.get("project_id", "default"),
                        tags=json.loads(meta.get("tags", "[]")),
                        confidence=float(meta.get("confidence", 1.0)),
                    )
                    self._storage[mid] = entry
                entries.append(entry)

        return self._apply_decay(entries)

    async def _search_builtin(
        self,
        query: str,
        limit: int,
        memory_type: str = None,
        user_id: str = None,
        project_id: str = None,
    ) -> list[MemoryEntry]:
        """内置关键词匹配 + 时间衰减"""
        query_lower = query.lower()
        scored = []

        for entry in self._storage.values():
            if memory_type and entry.type != memory_type:
                continue
            if user_id and entry.user_id != user_id:
                continue
            if project_id and entry.project_id != project_id:
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
        self._persist_builtin()

        return entries

    # ── 统计 ──

    @property
    def count(self) -> int:
        return len(self._storage)

    def list_entries(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        user_id: str = None,
        project_id: str = None,
        memory_type: str = None,
    ) -> list[MemoryEntry]:
        entries = [
            entry for entry in self._storage.values()
            if (not user_id or entry.user_id == user_id)
            and (not project_id or entry.project_id == project_id)
            and (not memory_type or entry.type == memory_type)
        ]
        entries.sort(key=lambda entry: entry.updated_at, reverse=True)
        return entries[offset:offset + limit]

    def stats(self) -> dict:
        types = {}
        for e in self._storage.values():
            types[e.type] = types.get(e.type, 0) + 1
        return {
            "total": len(self._storage),
            "by_type": types,
            "backend": self._backend,
        }
