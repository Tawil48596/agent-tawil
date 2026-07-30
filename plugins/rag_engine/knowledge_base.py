"""知识库管理 — 创建/更新/删除"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class KnowledgeBase:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    description: str = ""
    document_count: int = 0
    chunk_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)


class KnowledgeBaseManager:
    """知识库管理"""

    def __init__(self):
        self._kbs: dict[str, KnowledgeBase] = {}

    def create(self, name: str, description: str = "") -> KnowledgeBase:
        kb = KnowledgeBase(name=name, description=description)
        self._kbs[kb.id] = kb
        return kb

    def get(self, kb_id: str) -> Optional[KnowledgeBase]:
        return self._kbs.get(kb_id)

    def update(self, kb_id: str, name: str = None, description: str = None) -> bool:
        kb = self._kbs.get(kb_id)
        if not kb:
            return False
        if name:
            kb.name = name
        if description:
            kb.description = description
        kb.updated_at = datetime.now().isoformat()
        return True

    def delete(self, kb_id: str) -> bool:
        return self._kbs.pop(kb_id, None) is not None

    def list_all(self) -> list[KnowledgeBase]:
        return list(self._kbs.values())

    def add_document(self, kb_id: str, chunk_count: int = 1) -> None:
        kb = self._kbs.get(kb_id)
        if kb:
            kb.document_count += 1
            kb.chunk_count += chunk_count
            kb.updated_at = datetime.now().isoformat()
