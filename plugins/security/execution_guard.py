"""L2 执行拦截层 — 高危通配符拦截、路径白名单、网络出站控制、资源配额"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExecutionDecision:
    allowed: bool
    requires_approval: bool = False
    reason: str = ""
    sanitized_command: str | None = None
    resource_limits: dict[str, Any] | None = None


class ExecutionGuard:
    """L2: 工具执行前拦截器 (Pre-hook)"""

    # ── 绝对禁止的危险模式 ──
    BLOCKED_PATTERNS = [
        # 文件系统破坏
        (r"\brm\s+(-[rRf]+\s+)*[/~]", "递归删除根目录/家目录"),
        (r"\brm\s+(-[rRf]+\s+)*\*", "通配符递归删除"),
        (r"\b(mkfs\.|format\s+[cdefgh]:)", "磁盘格式化"),
        (r">\s*/dev/sd[a-z]", "直接写入块设备"),
        (r"\bdd\s+if=.*\s+of=/dev/", "dd 写入设备"),
        # 系统破坏
        (r"\b(chmod\s+(-[Rr]+\s+)?777\s+/)", "根目录权限开放"),
        (r"\b(chown\s+(-[Rr]+\s+)?[^/\s]*\s+/)", "根目录所有者变更"),
        (r"\b(kill\s+-9\s+1\b)", "杀死 init 进程"),
        # 网络危险
        (r"\b(curl|wget).*\|\s*(ba)?sh", "管道执行远程脚本"),
        (r"\b(nc\s+-[lL].*-[eE]\s+/bin/)", "netcat 反向 shell"),
        (r"\b(python|perl|ruby)\s+-[ce].*(socket|subprocess|os\.system)", "脚本语言反向连接"),
    ]

    # ── 需审批的危险模式 ──
    APPROVAL_PATTERNS = [
        (r"\bsudo\b", "提权操作"),
        (r"\b(git\s+push|git\s+merge|git\s+rebase)", "Git 远程操作"),
        (r"\b(pip|npm|cargo)\s+install", "包安装"),
        (r"\b(docker|kubectl|systemctl)\b", "容器/服务管理"),
        (r"\b(DROP\s+TABLE|DROP\s+DATABASE|DELETE\s+FROM)", "数据库破坏性操作"),
        (r"\b(shutdown|reboot|halt|poweroff)\b", "系统关机/重启"),
        (r"\bchmod\s+.*777", "权限过度开放"),
    ]

    # ── 允许的工作目录白名单 ──
    DEFAULT_WORKSPACE = os.path.expanduser("~/agent_workspace")

    def __init__(self, config: dict = None):
        cfg = config or {}
        sandbox_cfg = cfg.get("sandbox", {}) if isinstance(cfg, dict) else {}
        self._workspace = Path(sandbox_cfg.get("workspace", self.DEFAULT_WORKSPACE))
        self._network_enabled = sandbox_cfg.get("network_disabled", True) is False
        self._read_only = sandbox_cfg.get("read_only_root", True)
        self._memory_limit = sandbox_cfg.get("memory_limit", "512m")
        self._cpu_limit = sandbox_cfg.get("cpu_limit", 1.0)
        self._timeout = sandbox_cfg.get("timeout", 30)

    def check(self, command: str, tool_name: str = "", workdir: str = "") -> ExecutionDecision:
        """检查命令是否可执行，返回判决"""
        # 1. 绝对禁止检查
        for pattern, reason in self.BLOCKED_PATTERNS:
            if re.search(pattern, command):
                return ExecutionDecision(
                    allowed=False,
                    reason=f"🚫 已拦截危险操作: {reason}",
                )

        # 2. 工作目录检查
        if workdir and not self._is_safe_path(workdir):
            return ExecutionDecision(
                allowed=False,
                reason=f"🚫 工作目录不在允许范围内: {workdir}",
            )

        # 3. 需审批检查
        for pattern, reason in self.APPROVAL_PATTERNS:
            if re.search(pattern, command):
                return ExecutionDecision(
                    allowed=True,
                    requires_approval=True,
                    reason=f"⚠️ 需要审批: {reason}",
                    sanitized_command=command,
                    resource_limits={
                        "memory": self._memory_limit,
                        "cpu": self._cpu_limit,
                        "timeout": self._timeout,
                        "network": self._network_enabled,
                    },
                )

        # 4. 普通命令 — 放行（带资源限制）
        return ExecutionDecision(
            allowed=True,
            resource_limits={
                "memory": self._memory_limit,
                "cpu": self._cpu_limit,
                "timeout": self._timeout,
            },
        )

    def _is_safe_path(self, path: str) -> bool:
        """检查路径是否在允许的工作区内"""
        try:
            resolved = Path(path).resolve()
            workspace = self._workspace.resolve()
            return str(resolved).startswith(str(workspace))
        except (ValueError, OSError):
            return False

    @staticmethod
    def detect_dangerous_command(command: str) -> list[str]:
        """静态检测危险命令（兼容旧接口）"""
        warnings = []
        for pattern, reason in ExecutionGuard.BLOCKED_PATTERNS:
            if re.search(pattern, command):
                warnings.append(f"🚫 {reason}")
        for pattern, reason in ExecutionGuard.APPROVAL_PATTERNS:
            if re.search(pattern, command):
                warnings.append(f"⚠️ {reason}")
        return warnings
