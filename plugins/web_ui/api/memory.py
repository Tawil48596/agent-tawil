"""Memory API"""

from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


@router.get("")
async def list_memory(request: Request, limit: int = 20):
    ltm = request.app.state.long_term_memory
    entries = sorted(
        ltm._storage.values(),
        key=lambda entry: entry.created_at,
        reverse=True,
    )[:limit]
    return {
        "entries": [
            {
                "id": entry.id,
                "content": entry.content,
                "type": entry.type,
                "importance": entry.importance,
                "source_session": entry.source_session,
                "created_at": entry.created_at,
            }
            for entry in entries
        ],
        "total": ltm.count,
    }


@router.post("")
async def save_memory(body: dict, request: Request):
    from plugins.memory.long_term import MemoryEntry
    ltm = request.app.state.long_term_memory
    entry = MemoryEntry(id="", content=body.get("content", ""), type=body.get("type", "fact"), importance=body.get("importance", 0.5))
    eid = await ltm.save(entry)
    return {"id": eid}


@router.delete("/{entry_id}")
async def delete_memory(entry_id: str, request: Request):
    ltm = request.app.state.long_term_memory
    ok = await ltm.delete(entry_id)
    return {"ok": ok}


@router.delete("")
async def clear_memory(request: Request):
    ltm = request.app.state.long_term_memory
    await ltm.clear()
    return {"ok": True}


@router.post("/search")
async def search_memory(body: dict, request: Request):
    ltm = request.app.state.long_term_memory
    results = await ltm.search(body.get("query", ""), body.get("limit", 10))
    return {"results": [{"id": e.id, "content": e.content, "type": e.type, "importance": e.importance} for e in results]}


@router.post("/consolidate")
async def consolidate_memory(body: dict, request: Request):
    consolidator = request.app.state.memory_consolidator
    session_id = body.get("session_id", "")
    messages = body.get("messages", [])
    ids = await consolidator.consolidate(messages, session_id)
    return {"consolidated": len(ids), "ids": ids}


@router.put("/settings")
async def memory_settings(body: dict, request: Request):
    return {"ok": True, "settings": body}
