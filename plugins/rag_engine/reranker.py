"""重排序器 — Cross-Encoder 精排 + 轻量回退"""

from typing import Optional


class Reranker:
    """重排序器

    生产环境: bge-reranker-v2-m3 / Cohere Rerank
    开发环境: 基于查询词覆盖率的简单回退
    """

    def __init__(self, model_name: str = "simple"):
        self._model_name = model_name
        self._cross_encoder = None

    async def rerank(self, query: str, results: list,
                      top_k: int = 5) -> list:
        """重排序结果列表"""
        if not results:
            return []

        if self._cross_encoder:
            return await self._cross_encoder_rerank(query, results, top_k)
        else:
            return self._simple_rerank(query, results, top_k)

    async def _cross_encoder_rerank(self, query, results, top_k):
        """Cross-Encoder 精排 (需模型)"""
        pairs = [(query, r.content) for r in results]
        scores = self._cross_encoder.predict(pairs)
        for r, s in zip(results, scores):
            r.score = float(s)
        return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]

    def _simple_rerank(self, query: str, results: list, top_k: int) -> list:
        """基于查询词覆盖率 + 位置加权的简单重排"""
        query_words = set(query.lower().split())
        if not query_words:
            return results[:top_k]

        for i, r in enumerate(results):
            content_lower = r.content.lower()
            # 词覆盖率
            covered = sum(1 for w in query_words if w in content_lower)
            coverage = covered / len(query_words)
            # 位置加权 (越靠前略加分)
            position_bonus = 1.0 / (i + 2)
            # 综合
            r.score = coverage * 0.8 + position_bonus * 0.2 + r.score * 0.1

        return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
