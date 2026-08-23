"""通用工具函数"""

import json
import time
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any, TypeVar

T = TypeVar("T")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def now_ts() -> int:
    return int(time.time())


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return default


def safe_json_loads(s: str, default: Any = None) -> Any:
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default


def truncate(text: str, max_len: int = 200, suffix: str = "...") -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + suffix


def chunk_list(items: list[T], size: int) -> Iterator[list[T]]:
    """将列表按 size 分块"""
    for i in range(0, len(items), size):
        yield items[i : i + size]


async def async_collect(iterator: AsyncIterator[T]) -> list[T]:
    """收集 AsyncIterator 所有元素"""
    return [item async for item in iterator]
