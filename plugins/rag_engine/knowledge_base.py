"""Persistent knowledge-base and document metadata."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


def _now() -> str:
    return datetime.now().isoformat()


@dataclass
class DocumentRecord:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    source: str = ""
    size_bytes: int = 0
    chunk_count: int = 0
    chunk_strategy: str = "fixed"
    created_at: str = field(default_factory=_now)
    metadata: dict = field(default_factory=dict)


@dataclass
class KnowledgeBase:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    document_count: int = 0
    chunk_count: int = 0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: dict = field(default_factory=dict)
    documents: list[DocumentRecord] = field(default_factory=list)


class KnowledgeBaseManager:
    """Knowledge-base metadata persisted independently from vector storage."""

    def __init__(self, storage_path: str | Path = "data/rag_metadata.json"):
        self._storage_path = Path(storage_path)
        self._kbs: dict[str, KnowledgeBase] = {}
        self._load()

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
            for item in payload:
                documents = [
                    DocumentRecord(**document)
                    for document in item.pop("documents", [])
                ]
                kb = KnowledgeBase(**item, documents=documents)
                kb.document_count = len(documents)
                kb.chunk_count = sum(document.chunk_count for document in documents)
                self._kbs[kb.id] = kb
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            self._kbs = {}

    def _persist(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(kb) for kb in self._kbs.values()]
        temporary = self._storage_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self._storage_path)

    def create(self, name: str, description: str = "") -> KnowledgeBase:
        kb = KnowledgeBase(name=name.strip(), description=description.strip())
        self._kbs[kb.id] = kb
        self._persist()
        return kb

    def get(self, kb_id: str) -> Optional[KnowledgeBase]:
        return self._kbs.get(kb_id)

    def update(self, kb_id: str, name: str = None, description: str = None) -> bool:
        kb = self._kbs.get(kb_id)
        if not kb:
            return False
        if name is not None:
            kb.name = name.strip()
        if description is not None:
            kb.description = description.strip()
        kb.updated_at = _now()
        self._persist()
        return True

    def delete(self, kb_id: str) -> bool:
        deleted = self._kbs.pop(kb_id, None) is not None
        if deleted:
            self._persist()
        return deleted

    def list_all(self) -> list[KnowledgeBase]:
        return sorted(self._kbs.values(), key=lambda kb: kb.updated_at, reverse=True)

    def add_document(self, kb_id: str, document: DocumentRecord) -> bool:
        kb = self._kbs.get(kb_id)
        if not kb:
            return False
        kb.documents.append(document)
        kb.document_count = len(kb.documents)
        kb.chunk_count = sum(item.chunk_count for item in kb.documents)
        kb.updated_at = _now()
        self._persist()
        return True

    def list_documents(self, kb_id: str) -> list[DocumentRecord]:
        kb = self._kbs.get(kb_id)
        return list(kb.documents) if kb else []

    def delete_document(self, kb_id: str, document_id: str) -> bool:
        kb = self._kbs.get(kb_id)
        if not kb:
            return False
        before = len(kb.documents)
        kb.documents = [doc for doc in kb.documents if doc.id != document_id]
        if len(kb.documents) == before:
            return False
        kb.document_count = len(kb.documents)
        kb.chunk_count = sum(item.chunk_count for item in kb.documents)
        kb.updated_at = _now()
        self._persist()
        return True
