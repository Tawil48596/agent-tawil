"""文档索引器 — 分块 + 嵌入 + 存储"""

from typing import Any

from plugins.rag_engine.chunker.fixed_size import FixedSizeChunker
from plugins.rag_engine.chunker.semantic import SemanticChunker
from plugins.rag_engine.chunker.code_aware import CodeAwareChunker


class DocumentIndexer:
    """文档索引器 — 选择合适的 chunker 并生成 chunks"""

    CHUNKERS = {
        "fixed": FixedSizeChunker,
        "semantic": SemanticChunker,
        "code": CodeAwareChunker,
    }

    def __init__(self, vector_store=None, default_strategy: str = "fixed"):
        self._vector_store = vector_store
        self._default = default_strategy

    async def index(self, content: str, metadata: dict,
                     strategy: str = "fixed") -> list[dict]:
        """将内容分块并返回 chunks"""
        chunker_cls = self.CHUNKERS.get(strategy, FixedSizeChunker)
        chunker = chunker_cls()
        chunks = chunker.chunk(content)

        # 给每个 chunk 添加 metadata
        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                "content": chunk,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "chunk_count": len(chunks),
                    "strategy": strategy,
                },
            })

        return result


class ChunkResult:
    def __init__(self, content: str, metadata: dict = None):
        self.content = content
        self.metadata = metadata or {}
