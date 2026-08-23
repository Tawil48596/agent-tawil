"""混合检索 — 关键词 + 向量 + 时间衰减"""


class MemoryRetrieval:
    """记忆混合检索器"""

    def __init__(self, long_term_memory=None, short_term_memory=None, user_profile=None):
        self._ltm = long_term_memory
        self._stm = short_term_memory
        self._profile = user_profile
        self._decay_lambda = 0.01

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        include_short_term: bool = True,
        include_profile: bool = True,
    ) -> dict:
        """混合检索: 短期 + 长期 + 用户画像"""
        result = {"short_term": [], "long_term": [], "profile": {}}

        # 短期记忆
        if include_short_term and self._stm:
            stm_msgs = self._stm.get_recent(10)
            result["short_term"] = [
                m for m in stm_msgs if query.lower() in (m.get("content", "") or "").lower()
            ]

        # 长期记忆
        if self._ltm:
            entries = await self._ltm.search(query, limit)
            result["long_term"] = [
                {"content": e.content, "type": e.type, "importance": e.importance} for e in entries
            ]

        # 用户画像
        if include_profile and self._profile:
            result["profile"] = self._profile.to_dict()

        return result

    def inject_context(self, retrieval_result: dict) -> str:
        """将检索结果转为注入上下文的文本"""
        parts = []

        if retrieval_result.get("profile"):
            p = retrieval_result["profile"]
            prefs = p.get("preferences", {})
            if prefs:
                parts.append("用户偏好: " + ", ".join(f"{k}={v}" for k, v in prefs.items()))

        if retrieval_result.get("long_term"):
            parts.append("长期记忆:")
            for m in retrieval_result["long_term"][:5]:
                parts.append(f"- [{m['type']}] {m['content']}")

        if retrieval_result.get("short_term"):
            parts.append("近期相关对话:")
            for m in retrieval_result["short_term"][:3]:
                parts.append(f"- {m.get('content', '')[:200]}")

        return "\n".join(parts)
