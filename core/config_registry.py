"""配置注册表"""

import os
from pathlib import Path
from typing import Any

import yaml


class ConfigRegistry:
    """配置注册表 — 从 YAML + 环境变量加载，支持 ${ENV_VAR} 替换"""

    def __init__(self, config_path: str = "config.yaml"):
        import re
        self._path = Path(config_path)
        self._data: dict[str, Any] = {}
        self._re = re

        if self._path.exists():
            self._load()

    def _load(self) -> None:
        raw = self._path.read_text(encoding="utf-8")

        def _replacer(match):
            return os.environ.get(match.group(1), match.group(0))

        raw = self._re.sub(r"\$\{(\w+)\}", _replacer, raw)
        self._data = yaml.safe_load(raw) or {}

    def get(self, *keys: str, default: Any = None) -> Any:
        """嵌套获取配置: config.get('llm', 'default_model')"""
        value = self._data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
        return value if value is not None else default

    def set(self, *keys: str, value: Any) -> None:
        """嵌套设置配置"""
        d = self._data
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    def all(self) -> dict[str, Any]:
        return dict(self._data)

    def reload(self) -> None:
        self._data.clear()
        self._load()
