"""标题生成器 — LLM 自动生成会话标题"""

from typing import Optional


class Titleizer:
    """LLM 自动生成会话标题"""

    TITLE_PROMPT = """根据以下对话的第一条消息，生成一个简短的会话标题（不超过 20 个字符）。
只返回标题文本，不要加引号或任何前缀。

用户消息: {message}

标题:"""

    def __init__(self, model_router=None):
        self._router = model_router

    async def generate(self, first_message: str) -> str:
        """生成标题"""
        if not first_message:
            return "新对话"

        # 无 LLM 时的简单截断
        title = first_message.strip()
        # 去掉常见前缀
        for prefix in ["帮我", "请", "我想", "告诉我", "解释一下", "什么是"]:
            if title.startswith(prefix):
                title = title[len(prefix):]
        if len(title) > 20:
            title = title[:18] + "…"
        return title.strip() or "新对话"

    async def generate_with_llm(self, first_message: str) -> str:
        """使用 LLM 生成标题"""
        if not self._router or not first_message:
            return await self.generate(first_message)

        try:
            from litellm import acompletion
            from plugins.agent_engine.model_router import RouteRequest, TaskType

            route = self._router.route(RouteRequest(task_type=TaskType.FAST))
            response = await acompletion(
                model=f"{route.provider}/{route.model}",
                messages=[{"role": "user", "content": self.TITLE_PROMPT.format(message=first_message[:500])}],
                api_key=route.api_key,
                api_base=route.base_url if route.base_url else None,
                max_tokens=30,
            )
            title = (response.choices[0].message.content or "").strip().strip('"').strip("'")
            return title[:20] or "新对话"
        except Exception:
            return await self.generate(first_message)
