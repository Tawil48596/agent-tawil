"""短期记忆 — 当前会话消息窗口管理"""

from collections import deque


class ShortTermMemory:
    """短期记忆管理器 — 滑动窗口"""

    def __init__(self, max_messages: int = 50):
        self._max = max_messages
        self._messages: deque[dict] = deque(maxlen=max_messages)
        self._summary: str | None = None  # 溢出消息的摘要

    def add(self, message: dict) -> None:
        """添加消息。超出窗口的最旧消息自动丢弃。"""
        self._messages.append(message)
        if len(self._messages) >= self._max:
            self._compress_oldest()

    def add_batch(self, messages: list[dict]) -> None:
        for m in messages:
            self.add(m)

    def get_all(self) -> list[dict]:
        result = []
        if self._summary:
            result.append({"role": "system", "content": f"[历史摘要]\n{self._summary}"})
        result.extend(list(self._messages))
        return result

    def get_recent(self, n: int = 10) -> list[dict]:
        return list(self._messages)[-n:]

    def clear(self) -> None:
        self._messages.clear()
        self._summary = None

    @property
    def count(self) -> int:
        return len(self._messages)

    def _compress_oldest(self) -> None:
        """将最旧的 10 条消息压缩为摘要"""
        if len(self._messages) < 10:
            return
        old = [self._messages.popleft() for _ in range(min(10, len(self._messages)))]
        parts = [m.get("content", "")[:100] for m in old if m.get("content")]
        old_summary = " | ".join(parts)
        self._summary = (self._summary or "") + f"\n[更早] {old_summary}"
        if len(self._summary) > 2000:
            self._summary = self._summary[-2000:]
