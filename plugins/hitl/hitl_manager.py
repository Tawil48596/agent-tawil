"""HITL — Human-in-the-Loop 人机协作中断管理器"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger()


class HITLStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EDITED = "edited"       # 用户修改后放行
    TIMEOUT = "timeout"


class HITLType(str, Enum):
    APPROVAL = "approval"    # 审批确认
    EDIT = "edit"            # 允许编辑状态
    CONFIRM = "confirm"      # 二次确认


@dataclass
class HITLRequest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    session_id: str = ""
    type: HITLType = HITLType.APPROVAL
    title: str = ""
    description: str = ""
    agent_state: dict[str, Any] = field(default_factory=dict)
    proposed_action: dict[str, Any] = field(default_factory=dict)
    options: list[str] = field(default_factory=lambda: ["approve", "deny"])
    status: HITLStatus = HITLStatus.PENDING
    timeout: int = 300
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    user_edits: dict[str, Any] = field(default_factory=dict)


class HITLManager:
    """人机协作中断管理器

    使用场景:
      - git merge 前 → HITL 审批
      - 删除文件前 → HITL 二次确认
      - 高风险命令 → 用户可修改 Agent 状态后放行
    """

    def __init__(self, config: dict = None):
        cfg = config or {}
        hitl_cfg = cfg.get("hitl", {}) if isinstance(cfg, dict) else {}
        self._requests: dict[str, HITLRequest] = {}
        self._default_timeout = hitl_cfg.get("timeout", 300)
        self._on_request_callbacks: list[Callable] = []

    # ── 发起请求 ──

    async def request(self, session_id: str, hitl_type: HITLType,
                       title: str, description: str,
                       proposed_action: dict = None,
                       agent_state: dict = None,
                       timeout: int = None) -> HITLRequest:
        """发起 HITL 请求 — Agent 在此挂起等待"""
        req = HITLRequest(
            session_id=session_id,
            type=hitl_type,
            title=title,
            description=description,
            proposed_action=proposed_action or {},
            agent_state=agent_state or {},
            timeout=timeout or self._default_timeout,
        )
        self._requests[req.id] = req
        logger.info("HITL request created", id=req.id, type=hitl_type.value, title=title)

        # 通知前端/回调
        for cb in self._on_request_callbacks:
            try:
                await cb(req)
            except Exception:
                pass

        # 等待审批
        try:
            await asyncio.wait_for(
                self._wait_for_resolution(req.id),
                timeout=req.timeout,
            )
        except asyncio.TimeoutError:
            req.status = HITLStatus.TIMEOUT
            req.resolved_at = time.time()

        return req

    async def _wait_for_resolution(self, req_id: str):
        while req_id in self._requests:
            req = self._requests[req_id]
            if req.status not in (HITLStatus.PENDING,):
                return
            await asyncio.sleep(0.3)

    # ── 用户响应 ──

    def approve(self, req_id: str) -> bool:
        req = self._requests.get(req_id)
        if req and req.status == HITLStatus.PENDING:
            req.status = HITLStatus.APPROVED
            req.resolved_at = time.time()
            self._requests.pop(req_id, None)
            return True
        return False

    def deny(self, req_id: str, reason: str = "") -> bool:
        req = self._requests.get(req_id)
        if req and req.status == HITLStatus.PENDING:
            req.status = HITLStatus.DENIED
            req.resolved_at = time.time()
            req.description += f"\n拒绝原因: {reason}"
            self._requests.pop(req_id, None)
            return True
        return False

    def edit_and_approve(self, req_id: str, edits: dict) -> bool:
        """修改 Agent 状态后批准"""
        req = self._requests.get(req_id)
        if req and req.status == HITLStatus.PENDING:
            req.user_edits = edits
            req.agent_state.update(edits)  # 合并用户编辑
            req.status = HITLStatus.EDITED
            req.resolved_at = time.time()
            self._requests.pop(req_id, None)
            return True
        return False

    # ── 查询 ──

    def get_pending(self, session_id: str = "") -> list[HITLRequest]:
        pending = [r for r in self._requests.values() if r.status == HITLStatus.PENDING]
        if session_id:
            pending = [r for r in pending if r.session_id == session_id]
        return pending

    def get_request(self, req_id: str) -> Optional[HITLRequest]:
        return self._requests.get(req_id)

    def on_request(self, callback: Callable):
        self._on_request_callbacks.append(callback)

    def get_stats(self) -> dict:
        all_reqs = list(self._requests.values())
        return {
            "pending": sum(1 for r in all_reqs if r.status == HITLStatus.PENDING),
            "approved": sum(1 for r in all_reqs if r.status == HITLStatus.APPROVED),
            "denied": sum(1 for r in all_reqs if r.status == HITLStatus.DENIED),
            "edited": sum(1 for r in all_reqs if r.status == HITLStatus.EDITED),
            "timeout": sum(1 for r in all_reqs if r.status == HITLStatus.TIMEOUT),
        }
