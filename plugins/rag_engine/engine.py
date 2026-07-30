"""RAG 主引擎 — 索引 + 检索 + 注入"""

from typing import Any, Optional

import structlog

from plugins.rag_engine.indexer import DocumentIndexer
from plugins.rag_engine.retriever import HybridRetriever
from plugins.rag_engine.reranker import Reranker
from plugins.rag_engine.query_rewriter import QueryRewriter
from plugins.rag_engine.guardrail import RetrievalGuardrail
from plugins.rag_engine.vector_store import VectorStore

logger = structlog.get_logger()


class RAGEngine:
    """RAG 检索增强引擎"""

    def __init__(self, config: dict = None):
        cfg = config or {}
        rag_cfg = cfg.get("rag", {}) if isinstance(cfg, dict) else {}

        self._vector_store = VectorStore(config)
        self._indexer = DocumentIndexer(self._vector_store)
        self._retriever = HybridRetriever(self._vector_store, rag_cfg.get("hybrid_alpha", 0.7))
        self._reranker = Reranker()
        self._rewriter = QueryRewriter()
        self._guardrail = RetrievalGuardrail(
            min_score=rag_cfg.get("min_confidence", 0.3),
        )
        self._top_k = rag_cfg.get("retrieval_top_k", 10)
        self._rerank_top_k = rag_cfg.get("rerank_top_k", 5)
        self._kb_cache: dict[str, dict] = {}

    # ── Knowledge Base Management ──

    async def create_kb(self, name: str, description: str = "") -> str:
        import uuid
        kb_id = uuid.uuid4().hex[:8]
        self._kb_cache[kb_id] = {"id": kb_id, "name": name, "description": description}
        logger.info("KB created", id=kb_id, name=name)
        return kb_id

    async def delete_kb(self, kb_id: str):
        self._kb_cache.pop(kb_id, None)
        await self._vector_store.delete_collection(f"kb_{kb_id}")

    async def list_kbs(self) -> list[dict]:
        return list(self._kb_cache.values())

    # ── Document Indexing ──

    async def index_document(self, kb_id: str, content: str, metadata: dict = None,
                              chunk_strategy: str = "fixed") -> int:
        """索引单篇文档，返回 chunk 数量"""
        chunks = await self._indexer.index(content, metadata or {}, chunk_strategy)
        await self._vector_store.add(f"kb_{kb_id}", chunks)
        return len(chunks)

    async def index_documents(self, kb_id: str, documents: list[dict],
                               chunk_strategy: str = "fixed") -> int:
        """批量索引文档"""
        total = 0
        for doc in documents:
            n = await self.index_document(kb_id, doc.get("content", ""),
                                           doc.get("metadata"), chunk_strategy)
            total += n
        return total

    # ── Retrieval ──

    async def query(self, query: str, kb_ids: list[str] = None,
                     top_k: int = None, apply_guardrail: bool = True) -> dict:
        """检索查询 — 完整 pipeline"""
        top_k = top_k or self._top_k

        # 1. 查询改写 (HyDE / 多角度)
        rewritten_queries = await self._rewriter.rewrite(query)

        # 2. 混合检索 (Dense + BM25)
        # 给 kb_ids 添加 collection 前缀
        search_collections = [f"kb_{kbid}" for kbid in (kb_ids or [])] if kb_ids else None
        all_results = []
        for q in rewritten_queries:
            results = await self._retriever.search(q, search_collections, top_k * 2)
            all_results.extend(results)

        # 3. 融合去重 (RRF)
        fused = self._retriever.fuse(all_results, top_k)

        # 4. 重排序
        reranked = await self._reranker.rerank(query, fused, self._rerank_top_k)

        # 5. 检索守卫 — 低置信度阻断
        if apply_guardrail:
            filtered = self._guardrail.filter(query, reranked)
            if not filtered:
                return {
                    "results": [],
                    "blocked": True,
                    "message": "未在知识库中找到相关信息，请尝试其他查询或工具。",
                }
            reranked = filtered

        return {
            "results": [
                {"content": r.content, "score": r.score, "source": r.metadata.get("source", ""),
                 "chunk_id": r.chunk_id}
                for r in reranked
            ],
            "blocked": False,
            "query_rewritten": rewritten_queries[0] if rewritten_queries else query,
        }

    # ── Context Injection ──

    def inject_context(self, query_result: dict, max_tokens: int = 3000) -> str:
        """将检索结果注入 LLM 上下文"""
        results = query_result.get("results", [])
        if not results:
            return ""

        lines = ["## 检索到的相关知识\n"]
        for i, r in enumerate(results, 1):
            source = r.get("source", "unknown")
            content = r["content"]
            if len(content) > 2000:
                content = content[:2000] + "..."
            lines.append(f"### 来源 {i}: {source} (相关度: {r['score']:.2f})")
            lines.append(content)
            lines.append("")

        return "\n".join(lines)
