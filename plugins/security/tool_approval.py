"""危险工具审批流 — Pre-hook 挂起 + 超时自动拒绝 + Webhook 通知"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


@dataclass
class ApprovalRequest:
    id: str
    session_id: str
    tool_name: str
    command: str
    reason: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    timeout: int = 300  # 5 分钟超时


class ToolApproval:
    """危险工具审批管理器"""

    def __init__(self, config: dict = None):
        cfg = config or {}
        approval_cfg = cfg.get("tool_approval", {}) if isinstance(cfg, dict) else {}
        self._auto_approve: set[str] = set(approval_cfg.get("auto_approve_whitelist", []))
        self._pending: dict[str, ApprovalRequest] = {}
        self._default_timeout = approval_cfg.get("pending_timeout", 300)
        self._webhook_url = approval_cfg.get("notify_webhook", "")
        self._on_approval_callbacks: list[Callable] = []

    # ── 审批判断 ──

    def needs_approval(self, tool_name: str) -> bool:
        """工具是否需要审批"""
        return tool_name not in self._auto_approve

    def is_auto_approved(self, tool_name: str) -> bool:
        return tool_name in self._auto_approve

    # ── 审批请求生命周期 ──

    async def request_approval(
        self, session_id: str, tool_name: str, command: str, reason: str = ""
    ) -> ApprovalRequest:
        """发起审批请求，挂起等待"""
        import uuid
        req_id = uuid.uuid4().hex[:8]
        req = ApprovalRequest(
            id=req_id,
            session_id=session_id,
            tool_name=tool_name,
            command=command,
            reason=reason,
            timeout=self._default_timeout,
        )
        self._pending[req_id] = req

        # Webhook 通知
        if self._webhook_url:
            await self._notify_webhook(req)

        # 挂起等待审批结果
        try:
            await asyncio.wait_for(
                self._wait_for_decision(req_id),
                timeout=self._default_timeout,
            )
        except asyncio.TimeoutError:
            req.status = ApprovalStatus.TIMEOUT
            self._pending.pop(req_id, None)

        return req

    async def _wait_for_decision(self, req_id: str):
        """轮询等待审批决定"""
        while req_id in self._pending:
            req = self._pending[req_id]
            if req.status != ApprovalStatus.PENDING:
                return
            await asyncio.sleep(0.5)

    def approve(self, req_id: str) -> bool:
        """批准"""
        req = self._pending.get(req_id)
        if req and req.status == ApprovalStatus.PENDING:
            req.status = ApprovalStatus.APPROVED
            self._pending.pop(req_id, None)
            return True
        return False

    def deny(self, req_id: str) -> bool:
        """拒绝"""
        req = self._pending.get(req_id)
        if req and req.status == ApprovalStatus.PENDING:
            req.status = ApprovalStatus.DENIED
            self._pending.pop(req_id, None)
            return True
        return False

    def get_pending(self, session_id: str = "") -> list[ApprovalRequest]:
        """获取待审批列表"""
        if session_id:
            return [r for r in self._pending.values() if r.session_id == session_id]
        return list(self._pending.values())

    # ── 回调 ──

    def on_approval(self, callback: Callable):
        """注册审批事件回调"""
        self._on_approval_callbacks.append(callback)

    async def _notify_webhook(self, req: ApprovalRequest):
        """发送 Webhook 通知"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    self._webhook_url,
                    json={
                        "type": "tool_approval_required",
                        "id": req.id,
                        "session_id": req.session_id,
                        "tool": req.tool_name,
                        "command": req.command,
                        "reason": req.reason,
                    },
                    timeout=5,
                )
        except Exception:
            pass  # webhook 失败不应阻塞主流程
