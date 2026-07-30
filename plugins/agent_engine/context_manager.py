"""上下文管理器 — 上下文窗口监控 & 压缩触发"""

import tiktoken
from typing import Any


class ContextManager:
    """监控消息的 token 用量，触发压缩"""

    def __init__(self, model_encoding: str = "cl100k_base"):
        try:
            self._enc = tiktoken.get_encoding(model_encoding)
        except Exception:
            self._enc = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, messages: list[dict]) -> int:
        """估算消息列表的 token 数"""
        total = 0
        for msg in messages:
            content = msg.get("content", "") or ""
            total += len(self._enc.encode(content))
            # 工具调用额外 token
            for tc in msg.get("tool_calls", []) or []:
                total += len(self._enc.encode(str(tc)))
        # 每条消息约 4 token 的格式开销
        total += len(messages) * 4
        return total

    def needs_compression(self, messages: list[dict], context_length: int, threshold: float = 0.75) -> bool:
        """检查是否需要压缩 (当前使用率 > threshold)"""
        usage = self.count_tokens(messages)
        return usage > context_length * threshold

    def get_usage_ratio(self, messages: list[dict], context_length: int) -> float:
        """返回当前上下文使用率 (0.0 ~ 1.0+) """
        return self.count_tokens(messages) / context_length

    async def compress(
        self, messages: list[dict], route_result: Any, keep_recent: int = 10
    ) -> list[dict]:
        """压缩上下文: 保留 system + 最近 N 条消息 + 历史摘要"""
        from plugins.agent_engine.compression import compress_messages
        return await compress_messages(messages, route_result, keep_recent)
