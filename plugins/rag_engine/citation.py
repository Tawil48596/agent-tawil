"""引用追踪 — 检索结果附带 source_id，回复中标注来源"""

from typing import Optional


class CitationTracker:
    """RAG 引用追踪器"""

    def __init__(self):
        self._citations: list[dict] = []

    def add(self, source_id: str, chunk_id: str, content: str) -> str:
        """添加引用，返回引用标记 [1], [2], ..."""
        idx = len(self._citations) + 1
        self._citations.append({
            "index": idx,
            "source_id": source_id,
            "chunk_id": chunk_id,
            "content_preview": content[:200],
        })
        return f"[{idx}]"

    def annotate_response(self, response: str) -> str:
        """在回复末尾添加引用来源"""
        if not self._citations:
            return response
        lines = ["\n\n---\n**引用来源:**"]
        for c in self._citations:
            lines.append(f"  [{c['index']}] {c['source_id']}: {c['content_preview'][:100]}")
        return response + "\n".join(lines)

    def clear(self) -> None:
        self._citations.clear()

    def get_all(self) -> list[dict]:
        return list(self._citations)
