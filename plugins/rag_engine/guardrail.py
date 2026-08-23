"""RAG 检索守卫 — 低置信度阻断，防止错误上下文注入"""

import structlog

logger = structlog.get_logger()


class RetrievalGuardrail:
    """检索相关性过滤器"""

    def __init__(self, min_score: float = 0.3, max_empty_rounds: int = 2):
        self._min_score = min_score
        self._empty_rounds = 0
        self._max_empty_rounds = max_empty_rounds

    def filter(self, query: str, results: list) -> list:
        """过滤低置信度结果。全部偏低 → 返回空（阻断注入）"""
        if not results:
            self._empty_rounds += 1
            return []

        # 过滤
        filtered = [r for r in results if r.score >= self._min_score]

        if not filtered:
            self._empty_rounds += 1
            logger.info(
                "RAG guardrail blocked",
                query=query[:50],
                results_count=len(results),
                max_score=max(r.score for r in results),
            )
            return []

        self._empty_rounds = 0
        return filtered

    @property
    def should_declare_unknown(self) -> bool:
        """连续多轮无结果 → 建议声明知识缺失"""
        return self._empty_rounds >= self._max_empty_rounds
