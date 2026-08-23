"""分层上下文树构建器 — 常驻 + 动态 + 可折叠历史"""

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class NodeType(StrEnum):
    ENV = "env"  # 常驻环境
    WORKSPACE = "workspace"  # 动态工作区
    TASK = "task"  # 历史任务 (可折叠)
    STEP = "step"  # 任务步骤
    SUMMARY = "summary"  # 折叠后的摘要


class NodeStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    COLLAPSED = "collapsed"  # 已折叠为摘要
    EXPANDED = "expanded"  # 当前展开


@dataclass
class ContextNode:
    id: str
    type: NodeType
    content: str
    status: NodeStatus = NodeStatus.ACTIVE
    parent_id: str | None = None
    children: list["ContextNode"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    token_estimate: int = 0

    def add_child(self, child: "ContextNode"):
        child.parent_id = self.id
        self.children.append(child)

    def collapse(self, summary: str):
        """折叠节点 — 保留摘要"""
        self.type = NodeType.SUMMARY
        self.content = summary
        self.status = NodeStatus.COLLAPSED
        self.children = []
        self.token_estimate = len(summary) // 4

    def expand(self, original_content: str):
        """展开折叠的节点"""
        self.content = original_content
        self.status = NodeStatus.EXPANDED
        self.token_estimate = len(original_content) // 4


class ContextTree:
    """分层上下文树

    结构:
      L1: 环境设定 (常驻, ~1K tokens)
      L2: 实时工作区 (动态, ~50% 窗口)
      L3: 历史操作树 (可折叠, ~50% 窗口)
    """

    def __init__(
        self,
        max_total_tokens: int = 100000,
        l1_ratio: float = 0.02,
        l2_ratio: float = 0.48,
        l3_ratio: float = 0.50,
    ):
        self._max_tokens = max_total_tokens
        self._ratios = {"l1": l1_ratio, "l2": l2_ratio, "l3": l3_ratio}

        # 三层结构
        self._env: ContextNode | None = None  # L1
        self._workspace: ContextNode | None = None  # L2
        self._history_tasks: list[ContextNode] = []  # L3

    # ── L1: 环境设定 ──

    def set_environment(self, content: str):
        self._env = ContextNode(
            id="l1_env",
            type=NodeType.ENV,
            content=content,
            token_estimate=len(content) // 4,
        )

    # ── L2: 工作区 ──

    def update_workspace(self, content: str):
        self._workspace = ContextNode(
            id="l2_workspace",
            type=NodeType.WORKSPACE,
            content=content,
            token_estimate=len(content) // 4,
        )

    # ── L3: 历史操作 ──

    def add_task(self, task_id: str, description: str) -> ContextNode:
        node = ContextNode(
            id=task_id,
            type=NodeType.TASK,
            content=description,
            status=NodeStatus.ACTIVE,
        )
        self._history_tasks.append(node)
        self._auto_collapse()
        return node

    def add_step(
        self, task_id: str, step_id: str, content: str, status: NodeStatus = NodeStatus.COMPLETED
    ):
        task = self._find_task(task_id)
        if task:
            step = ContextNode(
                id=step_id,
                type=NodeType.STEP,
                content=content,
                status=status,
                parent_id=task_id,
                token_estimate=len(content) // 4,
            )
            task.add_child(step)

    def complete_task(self, task_id: str, summary: str):
        task = self._find_task(task_id)
        if task:
            task.status = NodeStatus.COMPLETED
            task.collapse(summary)

    def expand_task(self, task_id: str, full_content: str):
        """按需展开已折叠的历史任务"""
        task = self._find_task(task_id)
        if task and task.status == NodeStatus.COLLAPSED:
            task.expand(full_content)
            self._auto_collapse()  # 可能需要折叠其他任务

    # ── 序列化 ──

    def to_messages(self) -> list[dict]:
        """将上下文树转为 LLM 消息列表"""
        messages = []

        # L1: 环境
        if self._env:
            messages.append(
                {
                    "role": "system",
                    "content": self._env.content,
                }
            )

        # L2: 工作区状态
        if self._workspace:
            messages.append(
                {
                    "role": "system",
                    "content": f"[当前工作区状态]\n{self._workspace.content}",
                }
            )

        # L3: 历史树摘要
        if self._history_tasks:
            history_lines = ["[历史操作树]"]
            for task in self._history_tasks:
                if task.status == NodeStatus.COLLAPSED:
                    history_lines.append(f"  📁 {task.id}: {task.content} (已折叠)")
                elif task.status == NodeStatus.EXPANDED:
                    history_lines.append(f"  📂 {task.id}: {task.content}")
                    for step in task.children:
                        icon = "✓" if step.status == NodeStatus.COMPLETED else "✗"
                        history_lines.append(f"    {icon} {step.content[:200]}")
            messages.append(
                {
                    "role": "system",
                    "content": "\n".join(history_lines),
                }
            )

        return messages

    @property
    def total_tokens(self) -> int:
        total = self._env.token_estimate if self._env else 0
        total += self._workspace.token_estimate if self._workspace else 0
        total += sum(t.token_estimate for t in self._history_tasks)
        return total

    # ── 内部 ──

    def _find_task(self, task_id: str) -> ContextNode | None:
        for t in self._history_tasks:
            if t.id == task_id:
                return t
        return None

    def _auto_collapse(self):
        """自动折叠旧任务以保持在 token 预算内"""
        l3_budget = int(self._max_tokens * self._ratios["l3"])
        l3_used = sum(t.token_estimate for t in self._history_tasks)

        # 超预算 → 从最旧的任务开始折叠
        if l3_used > l3_budget and len(self._history_tasks) > 1:
            for task in sorted(self._history_tasks, key=lambda t: t.created_at):
                if l3_used <= l3_budget:
                    break
                if task.status not in (NodeStatus.COLLAPSED,):
                    summary = f"已完成: {task.content[:100]}"
                    old_tokens = task.token_estimate
                    task.collapse(summary)
                    l3_used -= old_tokens - task.token_estimate
