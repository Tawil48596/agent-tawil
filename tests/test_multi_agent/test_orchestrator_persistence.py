import asyncio
import json

import pytest

from plugins.multi_agent.orchestrator import (
    OrchestrationMode, Orchestrator, SubTask, TaskStatus,
)


@pytest.mark.asyncio
async def test_plan_persists_and_reloads(tmp_path):
    path = tmp_path / "plans.json"
    orchestrator = Orchestrator(storage_path=path)
    plan = await orchestrator.create_plan("Release", OrchestrationMode.PARALLEL,
                                          [SubTask(goal="test")])
    restored = Orchestrator(storage_path=path).get_plan(plan.id)
    assert restored is not None
    assert restored.title == "Release"


def test_running_plan_is_recovered_as_pending(tmp_path):
    path = tmp_path / "plans.json"
    path.write_text(json.dumps([{"id": "p1", "title": "Recover",
        "mode": "parallel", "status": "running", "created_at": 1,
        "updated_at": 1, "aggregate_result": None,
        "tasks": [{"id": "t1", "goal": "resume", "status": "running"}]}]))
    plan = Orchestrator(storage_path=path).get_plan("p1")
    assert plan.status == TaskStatus.PENDING
    assert plan.tasks[0].status == TaskStatus.PENDING
    assert "Recovered" in plan.tasks[0].error


@pytest.mark.asyncio
async def test_quota_and_progress(tmp_path):
    orchestrator = Orchestrator(storage_path=tmp_path / "plans.json", max_tasks_per_plan=1)
    with pytest.raises(ValueError, match="quota"):
        await orchestrator.create_plan("Too many", OrchestrationMode.PARALLEL,
                                       [SubTask(goal="a"), SubTask(goal="b")])
    plan = await orchestrator.create_plan("One", OrchestrationMode.PARALLEL,
                                          [SubTask(goal="a")])
    await orchestrator.execute(plan.id)
    assert orchestrator.list_plans()[0]["progress"] == 1.0


class SlowEngine:
    async def run(self, **kwargs):
        await asyncio.sleep(10)


@pytest.mark.asyncio
async def test_background_execution_can_be_cancelled(tmp_path):
    orchestrator = Orchestrator(SlowEngine(), storage_path=tmp_path / "plans.json")
    plan = await orchestrator.create_plan("Cancel", OrchestrationMode.PARALLEL,
                                          [SubTask(goal="slow")])
    await orchestrator.start(plan.id)
    await orchestrator.cancel(plan.id)
    await asyncio.sleep(0)
    assert plan.status == TaskStatus.CANCELLED
    assert plan.tasks[0].status == TaskStatus.CANCELLED
