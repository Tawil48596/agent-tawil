"""核心数据模型"""

from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def new_id() -> str:
    return uuid4().hex[:12]


# ── Session ──


class Session(BaseModel):
    id: str = Field(default_factory=new_id)
    title: Optional[str] = None
    source: str = "web"
    profile: Optional[str] = None
    parent_id: Optional[str] = None  # 分支来源
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Message ──


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any]
    result: Optional[str] = None
    status: str = "pending"  # pending | running | done | error


class Message(BaseModel):
    id: Optional[int] = None
    session_id: str
    parent_msg_id: Optional[int] = None  # 分支点
    role: str  # user | assistant | tool | system
    content: Optional[str] = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    token_count: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)


# ── Memory ──


class MemoryEntry(BaseModel):
    id: str = Field(default_factory=new_id)
    content: str
    embedding: Optional[list[float]] = None
    type: str = "fact"  # fact | preference | event | lesson
    importance: float = 0.5
    source_session: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_accessed_at: datetime = Field(default_factory=datetime.now)
    access_count: int = 0
    ttl: Optional[int] = None


# ── Tool ──


class ToolDefinition(BaseModel):
    name: str
    description: str
    toolset: str = "custom"
    parameters: dict[str, Any] = Field(default_factory=dict)
    requires_env: list[str] = Field(default_factory=list)
    requires_packages: list[str] = Field(default_factory=list)
    requires_system: list[str] = Field(default_factory=list)
    version: str = "0.1.0"
    author: str = ""
    tags: list[str] = Field(default_factory=list)
    is_dangerous: bool = False


# ── Agent ──


class SubAgentConfig(BaseModel):
    goal: str
    context: str = ""
    toolsets: list[str] = Field(default_factory=list)
    model: Optional[str] = None
    max_turns: int = 50
    role: str = "leaf"  # leaf | orchestrator
    timeout: int = 300
    retry_attempts: int = 2
    retry_backoff: str = "exponential"


class AgentResponse(BaseModel):
    text: str
    stop_reason: str = "complete"  # complete | max_turns | tool_error | content_filter | user_interrupt | timeout
    usage: dict[str, int] = Field(default_factory=dict)
    tool_calls: list[ToolCall] = Field(default_factory=list)


# ── Usage / Analytics ──


class UsageRecord(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    session_id: str = ""
    trace_id: str = Field(default_factory=new_id)
    provider: str = ""
    model: str = ""
    request_type: str = "chat"  # chat | tool_call | compression | embedding
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    tool_calls_count: int = 0


# ── Event ──


class Event(BaseModel):
    type: str
    source: str
    trace_id: str = Field(default_factory=new_id)
    timestamp: datetime = Field(default_factory=datetime.now)
    data: dict[str, Any] = Field(default_factory=dict)
