"""查询改写 — HyDE + 多角度查询"""

from typing import Optional


class QueryRewriter:
    """查询改写器

    HyDE (Hypothetical Document Embeddings):
      用户查询 → LLM 生成假设文档 → 用假设文档的 embedding 检索
      适用于短查询: "最好的 Python 框架" → "Django 和 FastAPI 是流行的 Python Web 框架..."

    多角度查询:
      用户查询 → 生成 3 个不同角度的查询 → 并行检索 → RRF 融合
    """

    def __init__(self, model_router=None):
        self._router = model_router

    async def rewrite(self, query: str) -> list[str]:
        """改写查询，返回多个变体"""
        queries = [query]  # 原始查询始终保留

        # 多角度扩展
        angles = self._multi_angle_expand(query)
        queries.extend(angles)

        return queries[:4]  # 最多 4 个变体

    def _multi_angle_expand(self, query: str) -> list[str]:
        """启发式多角度扩展 (不需要 LLM)"""
        variants = []

        # 技术角度
        if any(kw in query.lower() for kw in ["代码", "实现", "怎么写", "如何", "code"]):
            variants.append(f"实现方式 最佳实践 {query}")

        # 对比角度
        if any(kw in query.lower() for kw in ["对比", "比较", "区别", "哪个好", "选择"]):
            variants.append(f"技术对比 优缺点 {query}")

        # 问题角度
        if any(kw in query.lower() for kw in ["错误", "bug", "问题", "报错", "error"]):
            variants.append(f"常见问题 解决方案 {query}")

        return variants[:3]
