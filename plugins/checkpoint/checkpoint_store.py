"""检查点持久化 — Worker 异常退出后从断点续跑"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class Checkpoint:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    task_id: str = ""
    agent_id: str = ""
    stage: str = ""  # 执行阶段
    state: dict[str, Any] = field(default_factory=dict)  # Agent 内存快照
    blackboard_snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class CheckpointStore:
    """检查点存储 — 支持本地文件 + Redis"""

    def __init__(self, config: dict = None):
        cfg = config or {}
        cp_cfg = cfg.get("checkpoint", {}) if isinstance(cfg, dict) else {}
        self._backend = cp_cfg.get("backend", "file")
        self._dir = Path(cp_cfg.get("path", "data/checkpoints"))
        self._dir.mkdir(parents=True, exist_ok=True)
        self._redis = None
        self._latest: dict[str, Checkpoint] = {}  # task_id → latest checkpoint

    # ── 保存 ──

    async def save(self, checkpoint: Checkpoint) -> str:
        """保存检查点"""
        if self._backend == "file":
            checkpoint_id = self._save_to_file(checkpoint)
        elif self._backend == "redis" and self._redis:
            checkpoint_id = await self._save_to_redis(checkpoint)
        else:
            checkpoint_id = checkpoint.id
        self._latest[checkpoint.task_id] = checkpoint
        return checkpoint_id

    def _save_to_file(self, cp: Checkpoint) -> str:
        task_dir = self._dir / cp.task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        path = task_dir / f"{cp.id}.json"
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        payload = json.dumps(
            {
                "id": cp.id,
                "task_id": cp.task_id,
                "agent_id": cp.agent_id,
                "stage": cp.stage,
                "state": cp.state,
                "blackboard_snapshot": cp.blackboard_snapshot,
                "created_at": cp.created_at,
                "metadata": cp.metadata,
            },
            ensure_ascii=False,
            default=str,
        )
        try:
            temporary.write_text(payload, encoding="utf-8")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        logger.debug("Checkpoint saved", id=cp.id, task=cp.task_id, stage=cp.stage)
        return cp.id

    async def _save_to_redis(self, cp: Checkpoint) -> str:
        key = f"checkpoint:{cp.task_id}:{cp.id}"
        await self._redis.set(
            key,
            json.dumps(
                {
                    "id": cp.id,
                    "task_id": cp.task_id,
                    "agent_id": cp.agent_id,
                    "stage": cp.stage,
                    "state": cp.state,
                },
                ensure_ascii=False,
                default=str,
            ),
            ex=3600,
        )
        return cp.id

    # ── 加载 ──

    async def load_latest(self, task_id: str) -> Checkpoint | None:
        """加载最新检查点"""
        if task_id in self._latest:
            return self._latest[task_id]

        if self._backend == "file":
            return self._load_latest_from_file(task_id)
        return None

    def _load_latest_from_file(self, task_id: str) -> Checkpoint | None:
        task_dir = self._dir / task_id
        if not task_dir.exists():
            return None

        files = sorted(task_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
        if not files:
            return None

        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                cp = Checkpoint(
                    id=data["id"],
                    task_id=data["task_id"],
                    agent_id=data["agent_id"],
                    stage=data["stage"],
                    state=data["state"],
                    blackboard_snapshot=data.get("blackboard_snapshot", {}),
                    created_at=data["created_at"],
                    metadata=data.get("metadata", {}),
                )
            except (OSError, json.JSONDecodeError, KeyError, TypeError):
                logger.warning("Skipping corrupt checkpoint", path=str(path))
                continue
            self._latest[task_id] = cp
            return cp
        return None

    # ── 查询 ──

    def list_for_task(self, task_id: str) -> list[Checkpoint]:
        task_dir = self._dir / task_id
        if not task_dir.exists():
            return []
        checkpoints = []
        for f in sorted(task_dir.glob("*.json"), key=os.path.getmtime):
            try:
                data = json.loads(f.read_text())
                checkpoints.append(
                    Checkpoint(
                        id=data["id"],
                        task_id=data["task_id"],
                        agent_id=data["agent_id"],
                        stage=data["stage"],
                        created_at=data["created_at"],
                    )
                )
            except Exception:
                pass
        return checkpoints

    def get_stats(self) -> dict:
        task_dirs = list(self._dir.glob("*")) if self._dir.exists() else []
        return {
            "total_tasks": len(task_dirs),
            "tasks": [d.name for d in task_dirs if d.is_dir()],
        }


class RecoveryManager:
    """恢复管理器 — Worker 异常后从检查点续跑"""

    def __init__(self, checkpoint_store: CheckpointStore, blackboard=None):
        self._store = checkpoint_store
        self._blackboard = blackboard

    async def recover(self, task_id: str, agent_engine=None, orchestrator=None) -> dict:
        """从检查点恢复任务"""
        cp = await self._store.load_latest(task_id)
        if not cp:
            return {"error": f"No checkpoint found for task {task_id}"}

        logger.info(
            "Recovering from checkpoint", task_id=task_id, stage=cp.stage, checkpoint_id=cp.id
        )

        # 恢复黑板状态
        if self._blackboard and cp.blackboard_snapshot:
            self._blackboard.restore(cp.blackboard_snapshot)

        # 重建任务上下文
        return {
            "ok": True,
            "task_id": task_id,
            "stage": cp.stage,
            "state": cp.state,
            "checkpoint_id": cp.id,
        }

    async def retry_failed(self, task_id: str, orchestrator, plan_id: str) -> dict:
        """重试失败的任务"""
        plan = orchestrator.get_plan(plan_id)
        if not plan:
            return {"error": "Plan not found"}

        failed_tasks = [t for t in plan.tasks if t.status.value == "failed"]
        if not failed_tasks:
            return {"ok": True, "message": "No failed tasks to retry"}

        for task in failed_tasks:
            task.status = "pending"
            task.progress = 0.0
            task.error = None

        logger.info("Retrying failed tasks", count=len(failed_tasks))
        return {"ok": True, "retried": len(failed_tasks)}
