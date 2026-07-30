"""多智能体编排器 — 任务分解 + 分配 + 监控"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger()


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


class OrchestrationMode(str, Enum):
    PARALLEL = "parallel"        # 所有子任务并行
    CHAIN = "chain"              # A → B → C 串行
    HIERARCHICAL = "hierarchical"  # 树形委派


@dataclass
class SubTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    goal: str = ""
    context: str = ""
    toolsets: list[str] = field(default_factory=list)
    model: Optional[str] = None
    max_turns: int = 30
    timeout: int = 120
    retry_attempts: int = 2
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    agent_id: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    parent_id: Optional[str] = None  # 层级模式中的父任务
    dependencies: list[str] = field(default_factory=list)  # 依赖的任务 ID
    checkpoint_key: str = ""   # 黑板 Key
    progress: float = 0.0      # 0.0 - 1.0


@dataclass
class OrchestrationPlan:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    mode: OrchestrationMode = OrchestrationMode.PARALLEL
    tasks: list[SubTask] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: TaskStatus = TaskStatus.PENDING
    aggregate_result: Optional[str] = None


class Orchestrator:
    """多智能体编排器

    支持三种模式:
      - PARALLEL: 所有子任务并行执行，等待全部完成后聚合
      - CHAIN: A → B → C 串行执行，前一个的输出作为后一个的上下文
      - HIERARCHICAL: 树形层级，子编排器可再委派
    """

    def __init__(self, agent_engine=None, max_workers: int = 10):
        self._engine = agent_engine
        self._max_workers = max_workers
        self._semaphore = asyncio.Semaphore(max_workers)
        self._plans: dict[str, OrchestrationPlan] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._on_task_complete: list[Callable] = []

    # ── 计划管理 ──

    async def create_plan(self, title: str, mode: OrchestrationMode,
                           tasks: list[SubTask]) -> OrchestrationPlan:
        plan = OrchestrationPlan(title=title, mode=mode, tasks=tasks)
        self._plans[plan.id] = plan
        logger.info("Orchestration plan created", id=plan.id, title=title,
                     tasks=len(tasks), mode=mode.value)
        return plan

    async def execute(self, plan_id: str) -> OrchestrationPlan:
        """执行编排计划"""
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        plan.status = TaskStatus.RUNNING

        if plan.mode == OrchestrationMode.PARALLEL:
            await self._execute_parallel(plan)
        elif plan.mode == OrchestrationMode.CHAIN:
            await self._execute_chain(plan)
        elif plan.mode == OrchestrationMode.HIERARCHICAL:
            await self._execute_hierarchical(plan)

        plan.status = TaskStatus.COMPLETED
        return plan

    async def cancel(self, plan_id: str):
        plan = self._plans.get(plan_id)
        if plan:
            plan.status = TaskStatus.CANCELLED
            for task in plan.tasks:
                task.status = TaskStatus.CANCELLED

    # ── 执行模式 ──

    async def _execute_parallel(self, plan: OrchestrationPlan):
        """并行执行"""
        ready_tasks = [t for t in plan.tasks if not t.dependencies]
        dep_tasks = {t.id: t for t in plan.tasks if t.dependencies}

        # 先执行无依赖的任务
        coros = [self._execute_subtask(t, plan) for t in ready_tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)

        # 检查依赖满足的后续任务
        completed = {t.id for t in plan.tasks if t.status == TaskStatus.COMPLETED}
        while dep_tasks:
            ready = []
            for tid, task in list(dep_tasks.items()):
                if all(d in completed for d in task.dependencies):
                    ready.append(task)
                    del dep_tasks[tid]
            if not ready:
                break  # 循环依赖或全部完成
            coros = [self._execute_subtask(t, plan) for t in ready]
            await asyncio.gather(*coros, return_exceptions=True)
            completed = {t.id for t in plan.tasks if t.status == TaskStatus.COMPLETED}

    async def _execute_chain(self, plan: OrchestrationPlan):
        """串行执行 — 前一个输出传递到下一个"""
        prev_result = ""
        for task in plan.tasks:
            if prev_result:
                task.context += f"\n\n[上一步结果]\n{prev_result[:2000]}"
            await self._execute_subtask(task, plan)
            if task.status == TaskStatus.COMPLETED:
                prev_result = task.result or ""
            else:
                break  # 链式失败则停止

    async def _execute_hierarchical(self, plan: OrchestrationPlan):
        """层级执行 — 树形 BFS"""
        root_tasks = [t for t in plan.tasks if not t.parent_id]
        await self._execute_parallel_level(root_tasks, plan)

    async def _execute_parallel_level(self, tasks: list[SubTask], plan: OrchestrationPlan):
        coros = [self._execute_subtask(t, plan) for t in tasks]
        await asyncio.gather(*coros, return_exceptions=True)

    # ── 单任务执行 ──

    async def _execute_subtask(self, task: SubTask, plan: OrchestrationPlan):
        """执行单个子任务"""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

            for attempt in range(task.retry_attempts + 1):
                try:
                    if self._engine:
                        response = await asyncio.wait_for(
                            self._engine.run(
                                user_message=task.goal,
                                override_model=task.model,
                                history=[{"role": "system", "content": task.context}],
                            ),
                            timeout=task.timeout,
                        )
                        task.result = response.text
                        task.status = TaskStatus.COMPLETED
                    else:
                        # 无引擎 — 模拟执行
                        task.result = f"[Simulated] {task.goal}"
                        task.status = TaskStatus.COMPLETED

                    task.completed_at = time.time()
                    task.progress = 1.0

                    # 保存到黑板
                    if task.checkpoint_key:
                        self._save_checkpoint(task)

                    logger.info("Subtask completed", task_id=task.id,
                                 goal=task.goal[:50], attempt=attempt + 1)
                    break

                except asyncio.TimeoutError:
                    if attempt == task.retry_attempts:
                        task.status = TaskStatus.FAILED
                        task.error = f"Timeout after {task.retry_attempts+1} attempts"
                    else:
                        task.progress = 0.5 * (attempt + 1) / task.retry_attempts

                except Exception as e:
                    if attempt == task.retry_attempts:
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                    else:
                        await asyncio.sleep(2 ** attempt)  # 指数退避

            # 回调
            for cb in self._on_task_complete:
                try:
                    cb(task)
                except Exception:
                    pass

    def on_task_complete(self, callback: Callable):
        self._on_task_complete.append(callback)

    def _save_checkpoint(self, task: SubTask):
        """保存检查点到黑板（实际由 checkpoint 插件处理）"""
        pass  # 由外部黑板接口实现

    # ── 聚合 ──

    async def aggregate(self, plan_id: str, strategy: str = "concat") -> str:
        """聚合子任务结果"""
        plan = self._plans.get(plan_id)
        if not plan:
            return ""

        results = [t.result or t.error or "" for t in plan.tasks]
        results = [r for r in results if r]

        if strategy == "concat":
            return "\n\n---\n\n".join(results)
        elif strategy == "summary" and self._engine:
            combined = "\n".join(f"[Task {t.id}]: {t.result}" for t in plan.tasks if t.result)
            response = await self._engine.run(
                user_message=f"总结以下子任务结果:\n{combined}",
                override_model=None,
            )
            return response.text
        return "\n".join(results)

    # ── 查询 ──

    def get_plan(self, plan_id: str) -> Optional[OrchestrationPlan]:
        return self._plans.get(plan_id)

    def list_plans(self) -> list[dict]:
        return [
            {"id": p.id, "title": p.title, "mode": p.mode.value,
             "status": p.status.value, "tasks": len(p.tasks),
             "completed": sum(1 for t in p.tasks if t.status == TaskStatus.COMPLETED)}
            for p in self._plans.values()
        ]

    def get_progress(self, plan_id: str) -> Optional[float]:
        plan = self._plans.get(plan_id)
        if not plan or not plan.tasks:
            return None
        completed = sum(1 for t in plan.tasks if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED))
        return completed / len(plan.tasks)
