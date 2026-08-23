"""L3 输出过滤层 — API Key 掩码、PII 脱敏、敏感路径移除"""

import re
from dataclasses import dataclass, field


@dataclass
class OutputResult:
    text: str
    redactions: list[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""


class OutputGuard:
    """L3: 流式输出后处理过滤器 (Post-hook)"""

    # ── 强制掩码模式 (无论上下文，一律打码) ──
    HARD_REDACT = {
        # API Keys
        "openai_key": (r"sk-[a-zA-Z0-9\-]{20,}", "[OPENAI_KEY]"),
        "anthropic_key": (r"sk-ant-[a-zA-Z0-9\-_]{20,}", "[ANTHROPIC_KEY]"),
        "deepseek_key": (r"sk-[a-zA-Z0-9]{30,}", "[DEEPSEEK_KEY]"),
        "github_token": (r"gh[pousr]_[a-zA-Z0-9]{36}", "[GITHUB_TOKEN]"),
        "github_pat": (r"github_pat_[a-zA-Z0-9_]{20,}", "[GITHUB_PAT]"),
        # JWT
        "jwt": (r"eyJ[a-zA-Z0-9\-_]{10,}\.[a-zA-Z0-9\-_]{10,}\.[a-zA-Z0-9\-_]{10,}", "[JWT_TOKEN]"),
        # Cloud Keys
        "aws_access": (r"AKIA[0-9A-Z]{16}", "[AWS_ACCESS_KEY]"),
        "aws_secret": (r"(?<=AWS_SECRET_ACCESS_KEY=)[^\s]+", "[AWS_SECRET]"),
        "gcp_key": (r"AIza[0-9A-Za-z\-_]{35}", "[GCP_KEY]"),
        # Private Keys
        "private_key": (
            r"-----BEGIN\s?(RSA|EC|DSA|OPENSSH|PGP)\s?PRIVATE KEY-----"
            r"[\s\S]*?-----END\s?\1\s?PRIVATE KEY-----",
            "[PRIVATE_KEY]",
        ),
        # Connection strings
        "db_url": (r"(?:postgres|mysql|mongodb|redis)://[^:]+:[^@]+@", "[DB_URL_WITH_CRED]"),
    }

    # ── PII 掩码 ──
    PII_REDACT = {
        "email": (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]"),
        "phone_cn": (r"1[3-9]\d{9}", "[PHONE]"),
        "id_card": (r"\d{17}[\dXx]", "[ID_CARD]"),
        "credit_card": (r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[CREDIT_CARD]"),
        "ip_addr": (
            r"\b(?:10|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b",
            "[INTERNAL_IP]",
        ),
    }

    # ── NSFW 关键词 ──
    NSFW_PATTERNS = [
        r"(?i)\b(porn|xxx|adult\s*content|explicit\s*sexual)\b",
    ]

    def filter(self, text: str, check_nsfw: bool = True) -> OutputResult:
        """对输出文本执行 L3 安全处理"""
        redactions = []

        # 1. 硬性掩码 (最高优先级)
        for label, (pattern, replacement) in self.HARD_REDACT.items():
            matches = re.findall(pattern, text)
            if matches:
                redactions.append(f"{label}: {len(matches)} 处")
                text = re.sub(pattern, replacement, text)

        # 2. PII 掩码
        for label, (pattern, replacement) in self.PII_REDACT.items():
            matches = re.findall(pattern, text)
            if matches:
                redactions.append(f"PII/{label}: {len(matches)} 处")
                text = re.sub(pattern, replacement, text)

        # 3. NSFW 检测（阻断，不掩码）
        if check_nsfw:
            for pattern in self.NSFW_PATTERNS:
                if re.search(pattern, text):
                    return OutputResult(
                        text="",
                        blocked=True,
                        block_reason="内容被安全策略拦截",
                        redactions=redactions,
                    )

        return OutputResult(text=text, redactions=redactions)

    def filter_stream(self, text: str) -> str:
        """流式场景下的轻量过滤（只做硬掩码）"""
        for pattern, replacement in self.HARD_REDACT.values():
            text = re.sub(pattern, replacement, text)
        return text

    @staticmethod
    def filter_output(text: str) -> str:
        """静态过滤（兼容旧接口）"""
        guard = OutputGuard()
        return guard.filter(text).text
