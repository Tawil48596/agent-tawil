"""Evals + Trace API"""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/v1/evals", tags=["evals"])


# ── Eval Suite ──


@router.get("/suites")
async def list_suites(request: Request):
    runner = request.app.state.eval_runner
    return {"suites": runner.list_suites()}


@router.post("/suites/{name}/run")
async def run_suite(name: str, request: Request):
    runner = request.app.state.eval_runner
    engine = request.app.state.agent_engine

    async def agent_fn(input_text: str) -> str:
        resp = await engine.run(user_message=input_text)
        return resp.text

    report = await runner.run(name, agent_fn)
    return report


@router.get("/history")
async def eval_history(request: Request):
    return {"history": request.app.state.eval_runner.get_history()}


# ── Trace ──


@router.get("/traces")
async def list_traces(limit: int = 50, request: Request = None):
    collector = request.app.state.trace_collector
    return {"traces": collector.list_traces(limit)}


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, request: Request):
    collector = request.app.state.trace_collector
    trace = collector.get_trace(trace_id)
    if not trace:
        raise HTTPException(404, "Trace not found")
    return trace.to_dict()


@router.get("/traces/stats")
async def trace_stats(request: Request):
    return request.app.state.trace_collector.get_stats()
