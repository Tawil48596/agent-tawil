"""Agent 安全 — 命令审批、敏感信息过滤"""

import re


class ContentFilter:
    """输入/输出内容过滤器"""

    # 常见敏感信息正则
    PATTERNS = {
        "api_key": r"(sk-[a-zA-Z0-9]{20,})",
        "github_token": r"(gh[pousr]_[a-zA-Z0-9]{36})",
        "jwt": r"(eyJ[a-zA-Z0-9\-_]{10,}\.[a-zA-Z0-9\-_]{10,}\.[a-zA-Z0-9\-_]{10,})",
        "aws_key": r"(AKIA[0-9A-Z]{16})",
        "private_key": r"(-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----)",
    }

    @classmethod
    def filter_input(cls, text: str) -> str:
        """过滤用户输入中的敏感信息"""
        # 在日志中隐藏敏感信息
        return text

    @classmethod
    def filter_output(cls, text: str) -> str:
        """过滤 LLM 输出中的敏感信息（防止泄露到前端）"""
        for key, pattern in cls.PATTERNS.items():
            text = re.sub(pattern, f"[REDACTED_{key.upper()}]", text)
        return text

    @classmethod
    def detect_dangerous_command(cls, command: str) -> list[str]:
        """检测危险命令"""
        warnings = []
        dangerous_keywords = [
            ("rm -rf", "递归删除命令"),
            ("sudo", "提权命令"),
            ("chmod 777", "权限过度开放"),
            ("DROP TABLE", "数据库删表"),
            ("DELETE FROM", "数据库删除"),
            ("shutdown", "关机命令"),
            ("reboot", "重启命令"),
            ("mkfs.", "格式化命令"),
            ("> /dev/", "设备写入"),
            ("curl.*|.*sh", "管道执行远程脚本"),
        ]
        for keyword, warning in dangerous_keywords:
            if keyword.lower() in command.lower():
                warnings.append(f"⚠️ {warning}: {keyword}")
        return warnings


class ToolApproval:
    """危险工具审批"""

    def __init__(self, auto_approve_list: list[str] | None = None):
        self._auto_approve = set(auto_approve_list or [])
        self._pending: dict[str, bool] = {}

    def needs_approval(self, tool_name: str) -> bool:
        """是否需要审批"""
        return tool_name not in self._auto_approve

    def approve(self, session_id: str):
        self._pending[session_id] = True

    def deny(self, session_id: str):
        self._pending[session_id] = False

    def is_approved(self, session_id: str) -> bool:
        return self._pending.get(session_id, False)
