"""混合检索器 — 稠密向量 + BM25 稀疏检索 + RRF 融合"""

import math
from collections import Counter
from typing import Optional


class RetrievalResult:
    def __init__(self, content: str, score: float, chunk_id: str = "",
                 metadata: dict = None):
        self.content = content
        self.score = score
        self.chunk_id = chunk_id
        self.metadata = metadata or {}


class HybridRetriever:
    """混合检索: Dense (向量) + Sparse (BM25) → RRF 融合"""

    def __init__(self, vector_store, alpha: float = 0.7):
        self._vs = vector_store
        self._alpha = alpha  # Dense 权重 (1-alpha = BM25 权重)
        self._bm25_index: dict[str, list[str]] = {}  # collection → doc texts
        self._bm25_cache: dict[str, "BM25Scorer"] = {}

    async def search(self, query: str, kb_ids: list[str] = None,
                      top_k: int = 10) -> list[RetrievalResult]:
        results = []

        # 1. Dense 检索 (向量)
        dense_results = await self._vs.search(query, kb_ids, top_k * 2)
        for r in dense_results:
            results.append(RetrievalResult(
                content=r.get("content", ""),
                score=r.get("score", 0.0) * self._alpha,
                chunk_id=r.get("id", ""),
                metadata=r.get("metadata", {}),
            ))

        # 2. Sparse 检索 (BM25) — 如果有本地索引
        if kb_ids:
            for kb_id in kb_ids:
                if kb_id in self._bm25_cache:
                    bm25_results = self._bm25_cache[kb_id].search(query, top_k)
                    for content, score in bm25_results:
                        results.append(RetrievalResult(
                            content=content,
                            score=score * (1 - self._alpha),
                            metadata={"kb_id": kb_id, "method": "bm25"},
                        ))

        # 3. RRF 融合
        return self.fuse(results, top_k)

    def fuse(self, results: list[RetrievalResult], top_k: int) -> list[RetrievalResult]:
        """Reciprocal Rank Fusion — 去重 + 重排"""
        # 简单去重 (基于内容前缀)
        seen = set()
        unique = []
        for r in sorted(results, key=lambda x: x.score, reverse=True):
            key = r.content[:100]  # 前 100 字符作为去重 key
            if key not in seen:
                seen.add(key)
                unique.append(r)

        return unique[:top_k]

    def index_bm25(self, collection: str, documents: list[str]):
        """为 BM25 建立本地索引"""
        self._bm25_index[collection] = documents
        self._bm25_cache[collection] = BM25Scorer(documents)


class BM25Scorer:
    """简易 BM25 实现"""

    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75):
        self._docs = documents
        self._k1 = k1
        self._b = b
        self._doc_count = len(documents)
        self._avgdl = sum(len(d.split()) for d in documents) / max(self._doc_count, 1)
        self._df = Counter()  # document frequency
        for doc in documents:
            words = set(doc.lower().split())
            for w in words:
                self._df[w] += 1

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        query_words = query.lower().split()
        scored = []

        for doc in self._docs:
            score = self._score(query_words, doc)
            if score > 0:
                scored.append((doc, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _score(self, query_words: list[str], doc: str) -> float:
        doc_words = doc.lower().split()
        doc_len = len(doc_words)
        score = 0.0
        for word in query_words:
            tf = doc_words.count(word)
            if tf == 0:
                continue
            df = self._df.get(word, 0)
            idf = math.log((self._doc_count - df + 0.5) / (df + 0.5) + 1)
            numerator = tf * (self._k1 + 1)
            denominator = tf + self._k1 * (1 - self._b + self._b * doc_len / self._avgdl)
            score += idf * numerator / denominator
        return score
