"""记忆巩固 — 会话结束后提取关键信息写入长期记忆"""

from typing import Any, Optional

import structlog

from plugins.memory.long_term import LongTermMemory, MemoryEntry

logger = structlog.get_logger()


class MemoryConsolidator:
    """记忆巩固器 — 会话结束/压缩时提取关键信息"""

    CONSOLIDATION_PROMPT = """从以下对话中提取用户的关键信息。返回 JSON 数组，每个元素包含:
- content: 记忆内容 (一句话)
- type: 类型 (fact/preference/event/lesson)
- importance: 重要性 (0.0-1.0)

不要提取临时性信息或这轮对话特有的上下文。只提取长期有用的信息。

对话:
{conversation}

仅返回 JSON 数组，不要加任何前缀或解释。"""

    def __init__(self, long_term: LongTermMemory, model_router=None):
        self._ltm = long_term
        self._router = model_router

    async def consolidate(self, messages: list[dict],
                           session_id: str = "",
                           model_override: str = None) -> list[str]:
        """从对话中提取关键信息并写入长期记忆"""
        if not messages or len(messages) < 3:
            return []

        # 构建对话文本
        conversation = self._format_conversation(messages)
        if len(conversation) < 100:
            return []

        # 用 LLM 提取
        extracted = await self._extract_with_llm(conversation, model_override)
        if not extracted:
            return []

        # 写入长期记忆
        ids = []
        for item in extracted:
            entry = MemoryEntry(
                id="",
                content=item.get("content", ""),
                type=item.get("type", "fact"),
                importance=float(item.get("importance", 0.5)),
                source_session=session_id,
            )
            eid = await self._ltm.save(entry)
            if eid:
                ids.append(eid)

        logger.info("Memory consolidated", session_id=session_id,
                     extracted=len(extracted), saved=len(ids))
        return ids

    def _format_conversation(self, messages: list[dict]) -> str:
        lines = []
        for m in messages[-30:]:  # 只取最后 30 条
            role = m.get("role", "unknown")
            content = m.get("content", "")
            if content and isinstance(content, str):
                lines.append(f"{role}: {content[:500]}")
        return "\n".join(lines)

    async def _extract_with_llm(self, conversation: str,
                                 model_override: str = None) -> list[dict]:
        """用 LLM 提取关键信息"""
        if not self._router:
            # 无 LLM — 使用简单启发式
            return self._heuristic_extract(conversation)

        try:
            from litellm import acompletion
            from plugins.agent_engine.model_router import RouteRequest, TaskType

            route = self._router.route(RouteRequest(
                task_type=TaskType.SUMMARIZATION,
                override_model=model_override,
            ))

            response = await acompletion(
                model=f"{route.provider}/{route.model}",
                messages=[{
                    "role": "user",
                    "content": self.CONSOLIDATION_PROMPT.format(conversation=conversation),
                }],
                api_key=route.api_key,
                api_base=route.base_url if route.base_url else None,
                max_tokens=500,
            )

            import json
            text = response.choices[0].message.content or "[]"
            # 清洗可能的前缀
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
            return json.loads(text)

        except Exception as e:
            logger.warning("LLM extraction failed, using heuristic", error=str(e))
            return self._heuristic_extract(conversation)

    def _heuristic_extract(self, conversation: str) -> list[dict]:
        """无 LLM 时的简单启发式提取"""
        facts = []
        lines = conversation.split("\n")

        # 检测用户偏好
        preference_keywords = ["我喜欢", "我常用", "我习惯", "我偏好", "我的项目"]
        for line in lines:
            if line.startswith("user:") or line.startswith("user："):
                for kw in preference_keywords:
                    if kw in line:
                        facts.append({
                            "content": line.split(":", 1)[-1].strip()[:200],
                            "type": "preference",
                            "importance": 0.6,
                        })
                        break

        return facts[:5]
