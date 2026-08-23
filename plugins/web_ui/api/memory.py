"""Memory API"""

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


def _serialize(entry) -> dict:
    return {
        "id": entry.id,
        "content": entry.content,
        "type": entry.type,
        "importance": entry.importance,
        "source_session": entry.source_session,
        "source": entry.source,
        "user_id": entry.user_id,
        "project_id": entry.project_id,
        "tags": entry.tags,
        "confidence": entry.confidence,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


@router.get("")
async def list_memory(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    user_id: str = "",
    project_id: str = "",
    memory_type: str = "",
):
    ltm = request.app.state.long_term_memory
    entries = ltm.list_entries(
        limit=min(max(limit, 1), 100),
        offset=max(offset, 0),
        user_id=user_id or None,
        project_id=project_id or None,
        memory_type=memory_type or None,
    )
    return {
        "entries": [_serialize(entry) for entry in entries],
        "total": len(
            ltm.list_entries(
                limit=ltm.count or 1,
                user_id=user_id or None,
                project_id=project_id or None,
                memory_type=memory_type or None,
            )
        ),
    }


@router.post("")
async def save_memory(body: dict, request: Request):
    from plugins.memory.long_term import MemoryEntry

    ltm = request.app.state.long_term_memory
    content = str(body.get("content", "")).strip()
    if not content:
        raise HTTPException(400, "Memory content is required")
    entry = MemoryEntry(
        id="",
        content=content,
        type=body.get("type", "fact"),
        importance=float(body.get("importance", 0.5)),
        source_session=body.get("source_session"),
        source=body.get("source", "manual"),
        user_id=body.get("user_id", "local"),
        project_id=body.get("project_id", "default"),
        tags=list(body.get("tags", [])),
        confidence=float(body.get("confidence", 1.0)),
    )
    eid = await ltm.save(entry)
    return {"id": eid}


@router.patch("/{entry_id}")
async def update_memory(entry_id: str, body: dict, request: Request):
    ltm = request.app.state.long_term_memory
    entry = await ltm.update(entry_id, **body)
    if not entry:
        raise HTTPException(404, "Memory not found")
    return _serialize(entry)


@router.delete("/{entry_id}")
async def delete_memory(entry_id: str, request: Request):
    ltm = request.app.state.long_term_memory
    ok = await ltm.delete(entry_id)
    return {"ok": ok}


@router.delete("")
async def clear_memory(
    request: Request,
    user_id: str = "",
    project_id: str = "",
):
    ltm = request.app.state.long_term_memory
    await ltm.clear(user_id=user_id or None, project_id=project_id or None)
    return {"ok": True}


@router.post("/search")
async def search_memory(body: dict, request: Request):
    ltm = request.app.state.long_term_memory
    results = await ltm.search(
        body.get("query", ""),
        body.get("limit", 10),
        body.get("type"),
        body.get("user_id"),
        body.get("project_id"),
    )
    return {"results": [_serialize(entry) for entry in results]}


@router.post("/consolidate")
async def consolidate_memory(body: dict, request: Request):
    consolidator = request.app.state.memory_consolidator
    session_id = body.get("session_id", "")
    messages = body.get("messages", [])
    ids = await consolidator.consolidate(
        messages,
        session_id,
        user_id=body.get("user_id", "local"),
        project_id=body.get("project_id", "default"),
    )
    return {"consolidated": len(ids), "ids": ids}


@router.put("/settings")
async def memory_settings(body: dict, request: Request):
    return {"ok": True, "settings": body}
