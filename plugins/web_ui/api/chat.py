"""Chat API — 对话端点 (SSE 流式 + model 参数)"""

import json
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from plugins.agent_engine.model_router import TaskType

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# ── 请求/响应模型 ──


class ChatRequest(BaseModel):
    content: str
    attachments: list[dict] = Field(default_factory=list)
    model: Optional[str] = None       # ★ per-message 模型切换
    task_type: str = "reasoning"      # reasoning | coding | summarization
    prefer_provider: Optional[str] = None
    tools: Optional[list[str]] = None
    reasoning_effort: Literal["auto", "low", "medium", "high"] = "auto"
    retry: bool = False


class SessionCreate(BaseModel):
    title: Optional[str] = None
    source: str = "web"


class SessionUpdate(BaseModel):
    title: Optional[str] = None


# ── 内存存储 (Phase 1 — 后续替换为 SQLite) ──

_sessions: dict[str, dict] = {}
_messages: dict[str, list[dict]] = {}


def _append_user_message(session_id: str, content: str, retry: bool) -> list[dict]:
    session_messages = _messages.setdefault(session_id, [])
    is_same_pending_message = (
        retry
        and bool(session_messages)
        and session_messages[-1].get("role") == "user"
        and session_messages[-1].get("content") == content
    )
    if not is_same_pending_message:
        session_messages.append({"role": "user", "content": content})
    return session_messages


# ── Session endpoints ──


@router.post("/sessions")
async def create_session(body: SessionCreate):
    import uuid
    sid = uuid.uuid4().hex[:12]
    session = {
        "id": sid,
        "title": body.title or f"新对话 {sid[:6]}",
        "source": body.source,
        "created_at": __import__("datetime").datetime.now().isoformat(),
    }
    _sessions[sid] = session
    _messages[sid] = []
    return session


@router.get("/sessions")
async def list_sessions(limit: int = 50, offset: int = 0):
    sessions = list(_sessions.values())
    return {
        "items": sessions[offset:offset + limit],
        "total": len(sessions),
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    return _sessions[session_id]


@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, body: SessionUpdate):
    if session_id not in _sessions:
        raise HTTPException(404, "Session not found")
    if body.title:
        _sessions[session_id]["title"] = body.title
    return _sessions[session_id]


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    _sessions.pop(session_id, None)
    _messages.pop(session_id, None)
    return {"ok": True}


# ── Message endpoints ──


@router.post("/sessions/{session_id}/messages")
async def send_message(session_id: str, body: ChatRequest, request: Request):
    """发送消息 — SSE 流式响应，支持 per-message model 切换

    model 参数可覆盖默认模型，实现对话中自由切换:
      {"content": "...", "model": "claude-sonnet-4"}
      {"content": "...", "model": "gpt-4o"}
      {"content": "...", model 不传 → 使用默认路由
    """
    if session_id not in _sessions:
        raise HTTPException(404, f"Session {session_id} not found. Create one first.")

    # 从 app state 获取 engine（由 plugin 注册）
    engine = getattr(request.app.state, "agent_engine", None)
    router = getattr(request.app.state, "model_router", None)

    if engine is None or router is None:
        raise HTTPException(503, "Agent engine not initialized. Check plugin loading.")

    async def event_stream():
        _append_user_message(session_id, body.content, body.retry)

        yield {"event": "message", "data": json.dumps({"type": "thinking", "content": "思考中..."}, ensure_ascii=False)}

        task_type_map = {
            "reasoning": "reasoning",
            "coding": "coding",
            "summarization": "summarization",
        }
        task_type = TaskType(task_type_map.get(body.task_type, "reasoning"))

        registry = getattr(request.app.state, "tool_registry", None)
        enabled_tools = []
        if registry is not None:
            requested_tools = set(body.tools) if body.tools is not None else None
            enabled_tools = [
                tool.to_dict()
                for tool in registry.list_enabled()
                if not tool.is_dangerous
                and (requested_tools is None or tool.name in requested_tools)
                and registry.check_dependencies(tool)["available"]
            ]

        try:
            async for event in engine.run_stream(
                user_message=body.content,
                history=_messages.get(session_id, [])[:-1],
                enabled_tools=enabled_tools,
                override_model=body.model,
                task_type=task_type,
                reasoning_effort=None if body.reasoning_effort == "auto" else body.reasoning_effort,
            ):
                if event.get("type") == "done" and event.get("content"):
                    _messages.setdefault(session_id, []).append({
                        "role": "assistant",
                        "content": event["content"],
                        "model": event.get("model"),
                    })
                yield {"event": "message", "data": json.dumps(event, ensure_ascii=False, default=str)}

        except Exception as e:
            yield {"event": "error", "data": json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)}

    return EventSourceResponse(event_stream())


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str, limit: int = 100, offset: int = 0):
    msgs = _messages.get(session_id, [])
    return {
        "items": msgs[offset:offset + limit],
        "total": len(msgs),
    }


# ── Config endpoint (供前端模型选择器) ──


@router.get("/models")
async def list_models(request: Request):
    """返回可用模型列表 — 供前端下拉菜单"""
    router = getattr(request.app.state, "model_router", None)
    if router is None:
        return {"models": [], "default_model": None}
    return {
        "models": router.list_models(),
        "available_models": router.list_available_models(),
        "default_model": router._default_model,
        "fast_model": router._fast_model,
        "task_mapping": {
            "reasoning": router.get_model_for_task(TaskType.REASONING),
            "coding": router.get_model_for_task(TaskType.CODING),
            "summarization": router.get_model_for_task(TaskType.SUMMARIZATION),
        },
    }


# ── Fork / Merge / Compress ──


@router.post("/sessions/{session_id}/fork")
async def fork_session(session_id: str, body: dict, request: Request):
    """从指定消息 fork 分支"""
    at_message_id = body.get("at_message_id", 0)
    new_title = body.get("title")
    if session_id in _sessions:
        import uuid
        from datetime import datetime

        branch_id = uuid.uuid4().hex[:12]
        parent = _sessions[session_id]
        _sessions[branch_id] = {
            "id": branch_id,
            "title": new_title or f"{parent['title']} (分支)",
            "source": parent["source"],
            "parent_id": session_id,
            "created_at": datetime.now().isoformat(),
        }
        # Web sessions currently use the in-memory store and messages do not
        # expose stable database IDs. The UI forks at the latest visible
        # message, so copying the complete conversation is deterministic.
        _messages[branch_id] = [dict(message) for message in _messages.get(session_id, [])]
        return {"branch_id": branch_id}

    store = getattr(request.app.state, "session_store", None)
    if store:
        from plugins.conversation.session_branch import SessionBranch
        sb = SessionBranch(store._conn)
        branch_id = sb.fork(session_id, at_message_id, new_title)
        if branch_id:
            return {"branch_id": branch_id}
    return {"error": "Session store not available"}


@router.post("/sessions/{session_id}/merge")
async def merge_session(session_id: str, body: dict, request: Request):
    """合并分支到主会话"""
    branch_id = body.get("branch_id", "")
    strategy = body.get("strategy", "rebase")
    store = getattr(request.app.state, "session_store", None)
    if store and branch_id:
        from plugins.conversation.session_merge import SessionMerge, MergeStrategy
        sm = SessionMerge(store._conn)
        result = sm.merge(branch_id, MergeStrategy(strategy))
        return result
    return {"error": "Missing branch_id or session store"}


@router.post("/sessions/{session_id}/compress")
async def compress_session(session_id: str, request: Request):
    """手动触发上下文压缩"""
    return {"ok": True, "message": "Compression triggered"}


# ── Search / Export ──


@router.post("/sessions/search")
async def search_sessions(body: dict, request: Request):
    """全文搜索历史会话"""
    store = getattr(request.app.state, "session_store", None)
    if store:
        from plugins.conversation.search import ConversationSearch
        cs = ConversationSearch(store._conn)
        return cs.search_all(body.get("query", ""), body.get("limit", 20))
    return {"messages": [], "sessions": []}


@router.get("/sessions/{session_id}/export")
async def export_session(session_id: str, fmt: str = "markdown", request: Request = None):
    """导出会话"""
    store = getattr(request.app.state, "session_store", None)
    if store:
        from plugins.conversation.export import ConversationExporter
        ce = ConversationExporter(store._conn)
        if fmt == "jsonl":
            return {"format": "jsonl", "data": ce.export_jsonl(session_id)}
        return {"format": "markdown", "data": ce.export_markdown(session_id)}
    return {"error": "Session store not available"}
