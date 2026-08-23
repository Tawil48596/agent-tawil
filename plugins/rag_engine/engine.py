"""RAG 主引擎 — 索引 + 检索 + 注入"""

from dataclasses import asdict

import structlog

from plugins.rag_engine.guardrail import RetrievalGuardrail
from plugins.rag_engine.indexer import DocumentIndexer
from plugins.rag_engine.knowledge_base import DocumentRecord, KnowledgeBaseManager
from plugins.rag_engine.query_rewriter import QueryRewriter
from plugins.rag_engine.reranker import Reranker
from plugins.rag_engine.retriever import HybridRetriever
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
        self._kb_manager = KnowledgeBaseManager(
            rag_cfg.get("metadata_path", "data/rag_metadata.json")
        )

    # ── Knowledge Base Management ──

    async def create_kb(self, name: str, description: str = "") -> str:
        if not name.strip():
            raise ValueError("Knowledge base name is required")
        kb = self._kb_manager.create(name, description)
        logger.info("KB created", id=kb.id, name=kb.name)
        return kb.id

    async def delete_kb(self, kb_id: str) -> bool:
        deleted = self._kb_manager.delete(kb_id)
        await self._vector_store.delete_collection(f"kb_{kb_id}")
        return deleted

    async def list_kbs(self) -> list[dict]:
        result = []
        for kb in self._kb_manager.list_all():
            item = asdict(kb)
            item.pop("documents", None)
            result.append(item)
        return result

    async def list_documents(self, kb_id: str) -> list[dict]:
        return [asdict(document) for document in self._kb_manager.list_documents(kb_id)]

    # ── Document Indexing ──

    async def index_document(
        self, kb_id: str, content: str, metadata: dict = None, chunk_strategy: str = "fixed"
    ) -> int:
        """索引单篇文档，返回 chunk 数量"""
        result = await self.index_document_with_record(kb_id, content, metadata, chunk_strategy)
        return result["chunk_count"]

    async def index_document_with_record(
        self,
        kb_id: str,
        content: str,
        metadata: dict = None,
        chunk_strategy: str = "fixed",
    ) -> dict:
        if not self._kb_manager.get(kb_id):
            raise ValueError(f"Knowledge base '{kb_id}' not found")
        if not content.strip():
            raise ValueError("Document content is empty")

        import uuid

        metadata = dict(metadata or {})
        document_id = uuid.uuid4().hex[:12]
        source = str(metadata.get("source") or metadata.get("filename") or document_id)
        document_name = str(metadata.get("filename") or metadata.get("name") or source)
        normalized_metadata = {
            **metadata,
            "document_id": document_id,
            "kb_id": kb_id,
            "source": source,
        }
        chunks = await self._indexer.index(content, normalized_metadata, chunk_strategy)
        for index, chunk in enumerate(chunks):
            chunk["id"] = f"{document_id}_{index}"
        await self._vector_store.add(f"kb_{kb_id}", chunks)

        record = DocumentRecord(
            id=document_id,
            name=document_name,
            source=source,
            size_bytes=int(metadata.get("size", len(content.encode("utf-8")))),
            chunk_count=len(chunks),
            chunk_strategy=chunk_strategy,
            metadata={key: value for key, value in metadata.items() if key not in {"size"}},
        )
        self._kb_manager.add_document(kb_id, record)
        await self._refresh_sparse_index(kb_id)
        return asdict(record)

    async def delete_document(self, kb_id: str, document_id: str) -> bool:
        deleted = self._kb_manager.delete_document(kb_id, document_id)
        if not deleted:
            return False
        await self._vector_store.delete_document(f"kb_{kb_id}", document_id)
        await self._refresh_sparse_index(kb_id)
        return True

    async def _refresh_sparse_index(self, kb_id: str) -> None:
        collection = f"kb_{kb_id}"
        chunks = await self._vector_store.list_documents(collection)
        self._retriever.index_bm25(
            collection,
            [chunk.get("content", "") for chunk in chunks],
        )

    async def index_documents(
        self, kb_id: str, documents: list[dict], chunk_strategy: str = "fixed"
    ) -> int:
        """批量索引文档"""
        total = 0
        for doc in documents:
            n = await self.index_document(
                kb_id, doc.get("content", ""), doc.get("metadata"), chunk_strategy
            )
            total += n
        return total

    # ── Retrieval ──

    async def query(
        self, query: str, kb_ids: list[str] = None, top_k: int = None, apply_guardrail: bool = True
    ) -> dict:
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
                {
                    "content": r.content,
                    "score": r.score,
                    "source": r.metadata.get("source", ""),
                    "source_id": r.metadata.get("document_id", ""),
                    "document_id": r.metadata.get("document_id", ""),
                    "kb_id": r.metadata.get("kb_id", ""),
                    "chunk_id": r.chunk_id,
                    "chunk_index": r.metadata.get("chunk_index"),
                    "citation": {
                        "source": r.metadata.get("source", ""),
                        "document_id": r.metadata.get("document_id", ""),
                        "chunk_id": r.chunk_id,
                        "chunk_index": r.metadata.get("chunk_index"),
                    },
                }
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
