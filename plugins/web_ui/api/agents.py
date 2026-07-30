"""Multi-Agent + HITL API"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class CreateTaskRequest(BaseModel):
    title: str
    mode: str = "parallel"
    tasks: list[dict]


class HITLActionRequest(BaseModel):
    action: str = "approve"  # approve | deny | edit
    reason: str = ""
    edits: dict = {}


# ── Orchestration ──


@router.post("/tasks")
async def create_task(body: CreateTaskRequest, request: Request):
    orch = request.app.state.orchestrator
    from plugins.multi_agent.orchestrator import OrchestrationMode, SubTask

    mode = OrchestrationMode(body.mode)
    tasks = []
    for t_data in body.tasks:
        task = SubTask(
            goal=t_data.get("goal", ""),
            context=t_data.get("context", ""),
            toolsets=t_data.get("toolsets", []),
            timeout=t_data.get("timeout", 120),
            dependencies=t_data.get("dependencies", []),
        )
        tasks.append(task)

    plan = await orch.create_plan(body.title, mode, tasks)
    return {"plan_id": plan.id, "title": plan.title, "tasks": len(plan.tasks)}


@router.post("/tasks/{plan_id}/execute")
async def execute_task(plan_id: str, request: Request):
    orch = request.app.state.orchestrator
    plan = await orch.execute(plan_id)
    return {
        "plan_id": plan.id,
        "status": plan.status.value,
        "progress": orch.get_progress(plan_id),
        "tasks": [{"id": t.id, "goal": t.goal[:80], "status": t.status.value,
                    "result": (t.result or "")[:200]} for t in plan.tasks],
    }


@router.get("/tasks")
async def list_tasks(request: Request):
    orch = request.app.state.orchestrator
    return {"plans": orch.list_plans()}


@router.get("/tasks/{plan_id}")
async def get_task(plan_id: str, request: Request):
    orch = request.app.state.orchestrator
    plan = orch.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return {
        "id": plan.id, "title": plan.title, "mode": plan.mode.value,
        "status": plan.status.value, "progress": orch.get_progress(plan_id),
        "tasks": [{"id": t.id, "goal": t.goal, "status": t.status.value,
                    "result": t.result, "error": t.error,
                    "progress": t.progress} for t in plan.tasks],
    }


@router.post("/tasks/{plan_id}/cancel")
async def cancel_task(plan_id: str, request: Request):
    orch = request.app.state.orchestrator
    await orch.cancel(plan_id)
    return {"ok": True}


@router.post("/tasks/{plan_id}/retry")
async def retry_task(plan_id: str, request: Request):
    rm = request.app.state.recovery_manager
    orch = request.app.state.orchestrator
    return await rm.retry_failed("", orch, plan_id)


# ── HITL ──


@router.get("/hitl/pending")
async def pending_hitl(session_id: str = "", request: Request = None):
    hitl = request.app.state.hitl_manager
    pending = hitl.get_pending(session_id=session_id)
    return {
        "requests": [
            {"id": r.id, "type": r.type.value, "title": r.title,
             "description": r.description, "proposed_action": r.proposed_action,
             "agent_state": r.agent_state, "created_at": r.created_at,
             "timeout": r.timeout}
            for r in pending
        ],
    }


@router.post("/hitl/{req_id}/action")
async def hitl_action(req_id: str, body: HITLActionRequest, request: Request):
    hitl = request.app.state.hitl_manager

    if body.action == "approve":
        ok = hitl.approve(req_id)
    elif body.action == "deny":
        ok = hitl.deny(req_id, body.reason)
    elif body.action == "edit":
        ok = hitl.edit_and_approve(req_id, body.edits)
    else:
        raise HTTPException(400, f"Unknown action: {body.action}")

    if not ok:
        raise HTTPException(404, f"Request not found or already resolved: {req_id}")
    return {"ok": True, "action": body.action}


# ── Checkpoint ──


@router.get("/checkpoints/{task_id}")
async def list_checkpoints(task_id: str, request: Request):
    store = request.app.state.checkpoint_store
    return {"checkpoints": [
        {"id": c.id, "stage": c.stage, "created_at": c.created_at}
        for c in store.list_for_task(task_id)
    ]}


@router.post("/checkpoints/{task_id}/recover")
async def recover_task(task_id: str, request: Request):
    rm = request.app.state.recovery_manager
    result = await rm.recover(task_id)
    return result


# ── Blackboard ──


@router.get("/blackboard/{prefix}")
async def read_blackboard(prefix: str, request: Request):
    bb = request.app.state.blackboard
    return {"data": bb.read_all(prefix=prefix)}
