"""Persistent multi-agent orchestration with recovery, quotas and cancellation."""

import asyncio
import contextlib
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


class OrchestrationMode(StrEnum):
    PARALLEL = "parallel"
    CHAIN = "chain"
    HIERARCHICAL = "hierarchical"


@dataclass
class SubTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    goal: str = ""
    context: str = ""
    toolsets: list[str] = field(default_factory=list)
    model: str | None = None
    max_turns: int = 30
    timeout: int = 120
    retry_attempts: int = 2
    status: TaskStatus = TaskStatus.PENDING
    result: str | None = None
    error: str | None = None
    agent_id: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    parent_id: str | None = None
    dependencies: list[str] = field(default_factory=list)
    checkpoint_key: str = ""
    progress: float = 0.0
    attempt_count: int = 0


@dataclass
class OrchestrationPlan:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str = ""
    mode: OrchestrationMode = OrchestrationMode.PARALLEL
    tasks: list[SubTask] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: TaskStatus = TaskStatus.PENDING
    aggregate_result: str | None = None


class Orchestrator:
    def __init__(
        self,
        agent_engine=None,
        max_workers: int = 10,
        storage_path: str | Path = "data/orchestration/plans.json",
        max_tasks_per_plan: int = 20,
    ):
        self._engine = agent_engine
        self._max_workers = max_workers
        self._max_tasks_per_plan = max_tasks_per_plan
        self._semaphore = asyncio.Semaphore(max_workers)
        self._plans: dict[str, OrchestrationPlan] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._on_task_complete: list[Callable] = []
        self._storage_path = Path(storage_path)
        self._load()

    def _serialize(self, plan: OrchestrationPlan) -> dict:
        data = asdict(plan)
        data["mode"] = plan.mode.value
        data["status"] = plan.status.value
        for item, task in zip(data["tasks"], plan.tasks, strict=False):
            item["status"] = task.status.value
        return data

    def _persist(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self._storage_path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(
                [self._serialize(p) for p in self._plans.values()], ensure_ascii=False, indent=2
            ),
            encoding="utf-8",
        )
        temp.replace(self._storage_path)

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            recovered = False
            for raw in data:
                tasks = []
                for item in raw.pop("tasks", []):
                    item["status"] = TaskStatus(item.get("status", "pending"))
                    if item["status"] in (TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL):
                        item["status"] = TaskStatus.PENDING
                        item["error"] = "Recovered after service restart"
                        item["progress"] = 0.0
                        recovered = True
                    tasks.append(SubTask(**item))
                raw["mode"] = OrchestrationMode(raw.get("mode", "parallel"))
                raw["status"] = TaskStatus(raw.get("status", "pending"))
                if raw["status"] in (TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL):
                    raw["status"] = TaskStatus.PENDING
                    recovered = True
                plan = OrchestrationPlan(tasks=tasks, **raw)
                self._plans[plan.id] = plan
            if recovered:
                self._persist()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self._plans = {}

    def _validate(self, title: str, tasks: list[SubTask]) -> None:
        if not title.strip():
            raise ValueError("Plan title is required")
        if not tasks:
            raise ValueError("At least one task is required")
        if len(tasks) > self._max_tasks_per_plan:
            raise ValueError(f"Plan exceeds task quota ({self._max_tasks_per_plan})")
        ids = {task.id for task in tasks}
        if len(ids) != len(tasks):
            raise ValueError("Task ids must be unique")
        if any(not task.goal.strip() for task in tasks):
            raise ValueError("Every task must have a goal")
        if any(dep not in ids for task in tasks for dep in task.dependencies):
            raise ValueError("Task dependency does not exist")

    async def create_plan(
        self, title: str, mode: OrchestrationMode, tasks: list[SubTask]
    ) -> OrchestrationPlan:
        self._validate(title, tasks)
        plan = OrchestrationPlan(title=title, mode=mode, tasks=tasks)
        self._plans[plan.id] = plan
        self._persist()
        return plan

    async def start(self, plan_id: str) -> OrchestrationPlan:
        plan = self._require_plan(plan_id)
        active = self._running_tasks.get(plan_id)
        if active and not active.done():
            return plan
        self._running_tasks[plan_id] = asyncio.create_task(self.execute(plan_id))
        await asyncio.sleep(0)
        return plan

    async def execute(self, plan_id: str) -> OrchestrationPlan:
        plan = self._require_plan(plan_id)
        plan.status = TaskStatus.RUNNING
        plan.updated_at = time.time()
        self._persist()
        try:
            if plan.mode == OrchestrationMode.CHAIN:
                await self._execute_chain(plan)
            else:
                await self._execute_parallel(plan)
            if plan.status != TaskStatus.CANCELLED:
                plan.status = (
                    TaskStatus.FAILED
                    if any(t.status == TaskStatus.FAILED for t in plan.tasks)
                    else TaskStatus.COMPLETED
                )
        except asyncio.CancelledError:
            plan.status = TaskStatus.CANCELLED
            raise
        finally:
            plan.updated_at = time.time()
            self._persist()
        return plan

    async def cancel(self, plan_id: str) -> None:
        plan = self._require_plan(plan_id)
        plan.status = TaskStatus.CANCELLED
        for task in plan.tasks:
            if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                task.status = TaskStatus.CANCELLED
                task.error = "Cancelled by user"
        runner = self._running_tasks.get(plan_id)
        if runner and not runner.done():
            runner.cancel()
        plan.updated_at = time.time()
        self._persist()

    async def retry_failed(self, plan_id: str) -> OrchestrationPlan:
        plan = self._require_plan(plan_id)
        for task in plan.tasks:
            if task.status in (TaskStatus.FAILED, TaskStatus.CANCELLED):
                task.status = TaskStatus.PENDING
                task.error = None
                task.result = None
                task.progress = 0.0
        plan.status = TaskStatus.PENDING
        self._persist()
        return await self.start(plan_id)

    async def _execute_parallel(self, plan: OrchestrationPlan) -> None:
        remaining = {t.id: t for t in plan.tasks if t.status == TaskStatus.PENDING}
        while remaining:
            completed = {t.id for t in plan.tasks if t.status == TaskStatus.COMPLETED}
            ready = [t for t in remaining.values() if all(d in completed for d in t.dependencies)]
            if not ready:
                for task in remaining.values():
                    task.status = TaskStatus.FAILED
                    task.error = "Blocked or cyclic dependency"
                break
            await asyncio.gather(*(self._execute_subtask(t, plan) for t in ready))
            for task in ready:
                remaining.pop(task.id, None)

    async def _execute_chain(self, plan: OrchestrationPlan) -> None:
        previous = ""
        for task in plan.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            if previous:
                task.context += f"\n\n[Previous result]\n{previous[:2000]}"
            await self._execute_subtask(task, plan)
            if task.status != TaskStatus.COMPLETED:
                break
            previous = task.result or ""

    async def _execute_subtask(self, task: SubTask, plan: OrchestrationPlan) -> None:
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            self._persist()
            for attempt in range(task.retry_attempts + 1):
                task.attempt_count += 1
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
                    else:
                        task.result = f"[Simulated] {task.goal}"
                    task.status = TaskStatus.COMPLETED
                    task.progress = 1.0
                    task.completed_at = time.time()
                    break
                except asyncio.CancelledError:
                    task.status = TaskStatus.CANCELLED
                    task.error = "Cancelled by user"
                    raise
                except Exception as exc:
                    if attempt == task.retry_attempts:
                        task.status = TaskStatus.FAILED
                        task.error = str(exc)
                    else:
                        await asyncio.sleep(2**attempt)
            plan.updated_at = time.time()
            self._persist()
            for callback in self._on_task_complete:
                with contextlib.suppress(Exception):
                    callback(task)

    async def aggregate(self, plan_id: str, strategy: str = "concat") -> str:
        plan = self._require_plan(plan_id)
        results = [t.result or t.error or "" for t in plan.tasks]
        return "\n\n---\n\n".join(value for value in results if value)

    def _require_plan(self, plan_id: str) -> OrchestrationPlan:
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")
        return plan

    def on_task_complete(self, callback: Callable) -> None:
        self._on_task_complete.append(callback)

    def get_plan(self, plan_id: str) -> OrchestrationPlan | None:
        return self._plans.get(plan_id)

    def get_progress(self, plan_id: str) -> float | None:
        plan = self._plans.get(plan_id)
        if not plan or not plan.tasks:
            return None
        terminal = (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        return sum(1 for task in plan.tasks if task.status in terminal) / len(plan.tasks)

    def list_plans(self) -> list[dict]:
        return [
            {
                "id": p.id,
                "title": p.title,
                "mode": p.mode.value,
                "status": p.status.value,
                "tasks": len(p.tasks),
                "completed": sum(t.status == TaskStatus.COMPLETED for t in p.tasks),
                "failed": sum(t.status == TaskStatus.FAILED for t in p.tasks),
                "progress": self.get_progress(p.id),
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }
            for p in self._plans.values()
        ]

    def limits(self) -> dict:
        return {"max_workers": self._max_workers, "max_tasks_per_plan": self._max_tasks_per_plan}
