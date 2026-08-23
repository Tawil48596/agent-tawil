"""并行协作: A ‖ B ‖ C"""

import asyncio
from collections.abc import Callable


class ParallelPattern:
    """并行协作模式 — 所有任务同时执行"""

    async def execute(self, tasks: list[dict], executor: Callable) -> list[dict]:
        coros = [executor(task) for task in tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)
        return [
            r if not isinstance(r, Exception) else {"status": "failed", "error": str(r)}
            for r in results
        ]
