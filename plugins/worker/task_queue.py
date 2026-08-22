"""任务队列与 Worker Pool — FastAPI 无状态 + 重计算解耦"""

import asyncio
import inspect
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=__import__("time").time)


class TaskQueue:
    """内存任务队列 (Phase 1 — 后续升级到 Redis)"""

    def __init__(self, max_workers: int = 4):
        self._queue: asyncio.Queue[Task] = asyncio.Queue()
        self._tasks: dict[str, Task] = {}
        self._handlers: dict[str, Callable] = {}
        self._max_workers = max_workers
        self._workers: list[asyncio.Task] = []

    def register_handler(self, task_name: str, handler: Callable):
        """注册任务处理器"""
        self._handlers[task_name] = handler

    async def submit(self, name: str, payload: dict = None) -> Task:
        """提交任务到队列，立即返回 task_id"""
        if name not in self._handlers:
            raise ValueError(f"Unknown task: {name}. Registered: {list(self._handlers)}")
        task = Task(name=name, payload=payload or {})
        self._tasks[task.id] = task
        await self._queue.put(task)
        return task

    async def submit_and_wait(self, name: str, payload: dict = None, timeout: float = 60) -> Task:
        """提交任务并等待完成"""
        task = await self.submit(name, payload)
        start = __import__("time").time()
        while task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            if __import__("time").time() - start > timeout:
                task.status = TaskStatus.FAILED
                task.error = "Timeout waiting for task"
                break
            await asyncio.sleep(0.1)
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    async def start(self):
        """启动 Worker Pool"""
        self._workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self._max_workers)
        ]

    async def stop(self):
        """停止所有 Worker"""
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    async def _worker(self, worker_id: int):
        """Worker 主循环"""
        while True:
            try:
                task = await self._queue.get()
                task.status = TaskStatus.RUNNING

                handler = self._handlers.get(task.name)
                if handler:
                    try:
                        if inspect.iscoroutinefunction(handler):
                            task.result = await handler(**task.payload)
                        else:
                            task.result = await asyncio.to_thread(handler, **task.payload)
                        task.status = TaskStatus.COMPLETED
                    except Exception as e:
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                else:
                    task.status = TaskStatus.FAILED
                    task.error = f"No handler for {task.name}"

                self._queue.task_done()
            except asyncio.CancelledError:
                break


# ── 预定义任务处理器 ──

async def task_sandbox_exec(command: str, workdir: str = "") -> dict:
    """沙箱命令执行任务"""
    from plugins.security.sandbox import Sandbox
    sandbox = Sandbox()
    result = await sandbox.execute(command, workdir=workdir)
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
    }


async def task_repo_clone(owner: str, repo: str, branch: str = "main") -> dict:
    """GitHub 仓库克隆任务"""
    import subprocess, os
    workspace = os.path.expanduser("~/agent_workspace")
    target = os.path.join(workspace, f"{owner}_{repo}")
    url = f"https://github.com/{owner}/{repo}.git"
    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth", "1", "--branch", branch, url, target,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return {
        "success": proc.returncode == 0,
        "path": target if proc.returncode == 0 else "",
        "error": stderr.decode() if proc.returncode != 0 else "",
    }
