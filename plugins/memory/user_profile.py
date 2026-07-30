"""用户画像 — 偏好、环境、习惯"""

from typing import Any, Optional


class UserProfile:
    """用户画像管理"""

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.preferences: dict[str, Any] = {}
        self.environment: dict[str, Any] = {}
        self.habits: dict[str, Any] = {}
        self.facts: list[str] = []

    def set_preference(self, key: str, value: Any) -> None:
        self.preferences[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        return self.preferences.get(key, default)

    def set_environment(self, key: str, value: Any) -> None:
        self.environment[key] = value

    def record_habit(self, key: str, value: Any) -> None:
        self.habits[key] = value

    def add_fact(self, fact: str) -> None:
        if fact not in self.facts:
            self.facts.append(fact)

    def to_prompt(self) -> str:
        """转为可用于系统提示词的文本"""
        parts = []
        parts.append(f"用户 ID: {self.user_id}")

        if self.preferences:
            parts.append("偏好: " + ", ".join(f"{k}={v}" for k, v in self.preferences.items()))
        if self.habits:
            parts.append("习惯: " + ", ".join(f"{k}={v}" for k, v in self.habits.items()))
        if self.facts:
            parts.append("已知信息: " + "; ".join(self.facts[-10:]))

        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "preferences": dict(self.preferences),
            "environment": dict(self.environment),
            "habits": dict(self.habits),
            "facts": list(self.facts),
        }
