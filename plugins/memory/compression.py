"""上下文压缩 — 长上下文 → 结构化摘要 (会话结束后)"""


class MemoryCompressor:
    """会话结束后: 长上下文总结为结构化摘要，写入长期记忆"""

    COMPRESS_PROMPT = """从以下对话中提取关键信息。返回 JSON:
{
  "summary": "3-5句话的对话总结",
  "key_facts": ["关键事实1", "关键事实2"],
  "decisions": ["做出的决定"],
  "user_preferences": {"key": "value"}
}

对话:
{conversation}"""

    def __init__(self, model_router=None):
        self._router = model_router

    async def compress(self, messages: list[dict]) -> dict:
        """压缩对话为结构化摘要"""
        conversation = self._format(messages)
        if len(conversation) < 200:
            return {
                "summary": conversation,
                "key_facts": [],
                "decisions": [],
                "user_preferences": {},
            }

        if self._router:
            return await self._llm_compress(conversation)
        else:
            return self._heuristic_compress(messages)

    def _format(self, messages: list[dict]) -> str:
        lines = []
        for m in messages[-50:]:
            role = m.get("role", "?")
            content = m.get("content", "")
            if content and isinstance(content, str):
                lines.append(f"{role}: {content[:300]}")
        return "\n".join(lines)

    async def _llm_compress(self, conversation: str) -> dict:
        try:
            from litellm import acompletion

            from plugins.agent_engine.model_router import RouteRequest, TaskType

            route = self._router.route(RouteRequest(task_type=TaskType.SUMMARIZATION))
            response = await acompletion(
                model=f"{route.provider}/{route.model}",
                messages=[
                    {
                        "role": "user",
                        "content": self.COMPRESS_PROMPT.format(conversation=conversation),
                    }
                ],
                api_key=route.api_key,
                api_base=route.base_url if route.base_url else None,
                max_tokens=500,
            )
            import json

            return json.loads(response.choices[0].message.content or "{}")
        except Exception:
            return self._heuristic_compress([])

    def _heuristic_compress(self, messages: list[dict]) -> dict:
        facts, decisions, prefs = [], [], {}
        for m in messages:
            c = m.get("content", "")
            if not isinstance(c, str):
                continue
            if any(kw in c for kw in ["决定", "确认", "同意"]):
                decisions.append(c[:200])
            if any(kw in c for kw in ["偏好", "习惯", "常用", "喜欢"]):
                facts.append(c[:200])
        return {
            "summary": "",
            "key_facts": facts[:5],
            "decisions": decisions[:3],
            "user_preferences": prefs,
        }
