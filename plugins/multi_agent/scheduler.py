"""任务调度器 — 优先级、依赖图"""

import asyncio
from collections import deque
from typing import Any, Callable, Optional


class TaskScheduler:
    """多智能体任务调度器"""

    def __init__(self, max_concurrent: int = 5):
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue: deque[dict] = deque()
        self._results: dict[str, Any] = {}

    async def schedule(self, tasks: list[dict], executor: Callable) -> list[dict]:
        """按依赖图调度执行"""
        # 构建依赖图
        ready = deque()
        waiting: dict[str, dict] = {}

        for task in tasks:
            deps = task.get("dependencies", [])
            if not deps:
                ready.append(task)
            else:
                waiting[task["id"]] = task

        results = []
        running: list[asyncio.Task] = []

        while ready or running:
            # 启动就绪任务
            while ready and len(running) < self._max_concurrent:
                task = ready.popleft()
                running.append(asyncio.create_task(self._run_one(task, executor)))

            if not running:
                break

            # 等待任意一个完成
            done, running = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)

            for t in done:
                result = t.result()
                results.append(result)
                task_id = result.get("task_id", "")

                # 检查依赖满足的等待任务
                newly_ready = []
                for tid, wtask in list(waiting.items()):
                    if all(d in [r.get("task_id") for r in results] for d in wtask.get("dependencies", [])):
                        newly_ready.append(tid)
                for tid in newly_ready:
                    ready.append(waiting.pop(tid))

        return results

    async def _run_one(self, task: dict, executor: Callable) -> dict:
        async with self._semaphore:
            try:
                result = await executor(task)
                return {"task_id": task.get("id", ""), "status": "completed", "result": result}
            except Exception as e:
                return {"task_id": task.get("id", ""), "status": "failed", "error": str(e)}
