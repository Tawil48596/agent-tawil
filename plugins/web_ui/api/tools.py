"""Tool Market API + Generative UI"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


class ToolInstallRequest(BaseModel):
    name: str


class ExecutionResolveRequest(BaseModel):
    session_id: str
    call_id: str
    confirm_reconciled: bool = False


# ── Tool Registry ──


@router.get("")
async def list_tools(request: Request, query: str = "", toolset: str = "", tag: str = ""):
    reg = request.app.state.tool_registry
    tools = reg.search(query=query, toolset=toolset, tag=tag)
    return {"tools": [t.to_dict() for t in tools], "total": len(tools)}


@router.get("/detail/{name}")
async def get_tool(name: str, request: Request):
    tool = request.app.state.tool_registry.get(name)
    if not tool:
        raise HTTPException(404, f"Tool not found: {name}")
    return tool.to_dict()


@router.get("/detail/{name}/dependencies")
async def check_dependencies(name: str, request: Request):
    tool = request.app.state.tool_registry.get(name)
    if not tool:
        raise HTTPException(404, f"Tool not found: {name}")
    return request.app.state.tool_registry.check_dependencies(tool)


# ── Marketplace ──


@router.get("/marketplace/browse")
async def browse_marketplace(
    request: Request, query: str = "", tag: str = "", sort: str = "downloads", limit: int = 20
):
    mp = request.app.state.marketplace
    entries = mp.browse(query=query, tag=tag, sort_by=sort, limit=limit)
    return {"items": [vars(e) for e in entries], "total": len(entries)}


@router.post("/marketplace/{name}/install")
async def install_tool(name: str, request: Request):
    mp = request.app.state.marketplace
    result = await mp.install(name)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/marketplace/{name}/uninstall")
async def uninstall_tool(name: str, request: Request):
    mp = request.app.state.marketplace
    result = await mp.uninstall(name)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/marketplace/{name}/update")
async def update_tool(name: str, request: Request):
    mp = request.app.state.marketplace
    result = await mp.update(name)
    return result


@router.get("/packages")
async def package_status(request: Request):
    return {"packages": request.app.state.tool_package_store.status()}


@router.post("/packages/{name}/rollback")
async def rollback_package(name: str, request: Request, version: str = ""):
    try:
        return request.app.state.tool_package_store.rollback(name, version or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


# ── Stats ──


@router.get("/stats")
async def tool_stats(request: Request):
    reg = request.app.state.tool_registry
    mp = request.app.state.marketplace
    return {
        "registry": reg.get_stats(),
        "marketplace": mp.get_stats(),
        "dangerous_tools": reg.get_dangerous_tools(),
    }


@router.post("/executions/resolve")
async def resolve_uncertain_execution(body: ExecutionResolveRequest, request: Request):
    """Clear an uncertain call only after a human reconciles its external effect."""
    if not body.confirm_reconciled:
        raise HTTPException(400, "Explicit reconciliation confirmation is required")
    ledger = request.app.state.execution_ledger
    if not ledger.resolve_uncertain(body.session_id, body.call_id):
        raise HTTPException(409, "Execution is not in an uncertain state")
    audit = getattr(request.app.state, "audit_log", None)
    if audit:
        audit.record(
            "tool.execution_resolved",
            session_id=body.session_id,
            call_id=body.call_id,
        )
    return {"ok": True, "session_id": body.session_id, "call_id": body.call_id}
