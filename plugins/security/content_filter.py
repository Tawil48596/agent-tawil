"""L1 输入过滤层 — 提示词越权注入检测、Jailbreak 拦截、PII 扫描"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FilterResult:
    passed: bool
    risk_level: str = "none"  # none | low | medium | high | critical
    warnings: list[str] = field(default_factory=list)
    sanitized: Optional[str] = None  # 净化后的文本


class ContentFilter:
    """L1: 输入内容安全过滤器"""

    # ── 提示词越权注入特征 ──
    JAILBREAK_PATTERNS = [
        r"(?i)(ignore|forget|disregard)\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
        r"(?i)(you\s+are\s+now|act\s+as\s+if\s+you\s+are|pretend\s+to\s+be)\s+(DAN|jailbreak|evil|unfiltered)",
        r"(?i)(system\s*:\s*|\[system\]|<\s*system\s*>)\s*(override|bypass|new\s+prompt)",
        r"(?i)(respond\s+as\s+a\s+different\s+(model|ai|assistant))",
        r"(?i)(do\s+not\s+follow|break\s+out\s+of|escape\s+from)\s+(your\s+)?(role|character|programming)",
        r"(?i)from\s+now\s+on\s+you\s+(are|will\s+be)\s+(a\s+)?(different|new)",
    ]

    # ── PII 检测模式 ──
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone_cn": r"1[3-9]\d{9}",
        "id_card_cn": r"\d{17}[\dXx]",
        "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "ssn_us": r"\b\d{3}-\d{2}-\d{4}\b",
    }

    # ── 内容特征检测 ──
    DANGEROUS_CONTENT = [
        (r"(?i)(hack|exploit|backdoor|crack)\s+(the|this|into|ing)", "攻击性指令"),
        (r"(?i)(generate|create|write)\s+(malware|ransomware|virus|worm|trojan)", "恶意代码生成"),
        (r"(?i)(steal|phish|spoof|impersonate)\s+(password|credential|identity)", "凭证窃取"),
        (r"(?i)(ddos|denial.of.service|flood)\s+(attack|target)", "拒绝服务攻击"),
    ]

    def check_input(self, text: str, user_id: str = "") -> FilterResult:
        """对用户输入执行 L1 安全检查"""
        if not text or not text.strip():
            return FilterResult(passed=True)

        warnings = []
        risk = "none"

        # 1. Jailbreak 检测
        for pattern in self.JAILBREAK_PATTERNS:
            if re.search(pattern, text):
                warnings.append(f"检测到提示词越权注入: {pattern}")

        # 2. 危险内容检测
        for pattern, label in self.DANGEROUS_CONTENT:
            if re.search(pattern, text):
                warnings.append(f"检测到危险内容: {label}")

        # 3. PII 检测（警告但不阻断）
        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                warnings.append(f"检测到 PII ({pii_type}): {len(matches)} 处匹配")

        # 4. 输入长度异常
        if len(text) > 100000:
            warnings.append(f"输入长度异常: {len(text)} 字符")
            risk = "medium"

        # 定级
        if any("越权注入" in w for w in warnings):
            risk = "high"
        if any("恶意代码" in w for w in warnings) or any("攻击" in w for w in warnings):
            risk = "critical"

        if risk == "critical":
            return FilterResult(passed=False, risk_level=risk, warnings=warnings)
        elif risk == "high":
            return FilterResult(passed=False, risk_level=risk, warnings=warnings,
                              sanitized=self._sanitize(text))
        else:
            return FilterResult(passed=True, risk_level=risk, warnings=warnings)

    def _sanitize(self, text: str) -> str:
        """PII 脱敏"""
        for pii_type, pattern in self.PII_PATTERNS.items():
            text = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", text)
        return text

    @staticmethod
    def filter_input(text: str) -> str:
        """简单兼容接口 — 返回原文本"""
        return text
