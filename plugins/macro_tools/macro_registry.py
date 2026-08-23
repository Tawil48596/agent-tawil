"""宏工具注册与执行 — 批量依赖调用打包 + 自动发现"""

import asyncio
import inspect
from collections import defaultdict
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger()


class MacroTool:
    """宏工具 — 多步依赖调用打包"""

    def __init__(self, name: str, description: str, steps: list[str],
                 executor: Callable):
        self.name = name
        self.description = description
        self.steps = steps  # 依赖的工具名列表
        self.executor = executor
        self.call_count = 0
        self.total_latency_ms = 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.call_count, 1)


class MacroRegistry:
    """宏工具注册表 + 自动序列发现"""

    def __init__(self):
        self._macros: dict[str, MacroTool] = {}
        self._call_sequences: list[list[str]] = []  # 记录所有调用序列
        self._sequence_counter: dict[str, int] = defaultdict(int)

    # ── 注册 ──

    def register(self, name: str, description: str, steps: list[str],
                 executor: Callable):
        macro = MacroTool(name, description, steps, executor)
        self._macros[name] = macro
        logger.info("Macro registered", name=name, steps=steps)

    def list_all(self) -> list[dict]:
        return [
            {"name": m.name, "description": m.description,
             "steps": m.steps, "call_count": m.call_count,
             "avg_latency_ms": round(m.avg_latency_ms, 1)}
            for m in self._macros.values()
        ]

    # ── 执行 ──

    async def execute(self, name: str, tool_dispatcher=None, **kwargs) -> dict:
        """执行宏工具"""
        macro = self._macros.get(name)
        if not macro:
            return {"error": f"Unknown macro: {name}"}

        import time
        start = time.time()

        try:
            if inspect.iscoroutinefunction(macro.executor):
                result = await macro.executor(**kwargs)
            else:
                result = macro.executor(**kwargs)

            macro.call_count += 1
            macro.total_latency_ms += (time.time() - start) * 1000

            return {"result": result, "macro": name, "steps_executed": len(macro.steps)}
        except Exception as e:
            return {"error": str(e), "macro": name}

    # ── 序列发现 ──

    def record_sequence(self, tool_names: list[str]):
        """记录一次工具调用序列"""
        self._call_sequences.append(tool_names)
        key = "→".join(tool_names)
        self._sequence_counter[key] += 1

    def suggest_macros(self, min_frequency: int = 10) -> list[dict]:
        """建议创建宏的频繁序列"""
        suggestions = []
        for seq_key, count in self._sequence_counter.items():
            if count >= min_frequency:
                tool_names = seq_key.split("→")
                suggestions.append({
                    "sequence": tool_names,
                    "frequency": count,
                    "suggested_name": "_".join(tool_names).replace("-", "_"),
                })
        return sorted(suggestions, key=lambda x: x["frequency"], reverse=True)[:5]

    def get_stats(self) -> dict:
        return {
            "total_macros": len(self._macros),
            "total_calls": sum(m.call_count for m in self._macros.values()),
            "sequences_recorded": len(self._call_sequences),
            "suggestions": len(self.suggest_macros()),
        }


# ── 内置宏工具 ──


async def macro_repo_explore(tool_dispatcher, owner: str, repo: str,
                              target_path: str = "") -> dict:
    """list_files → read_file 自动串联"""
    files = await tool_dispatcher._execute_one({
        "function": {"name": "github_list_files",
                      "arguments": f'{{"owner": "{owner}", "repo": "{repo}", "path": "{target_path}"}}'}
    })
    file_list = files.get("output", "[]")
    import json
    try:
        items = json.loads(file_list) if isinstance(file_list, str) else file_list
        items = items.get("items", []) if isinstance(items, dict) else []
    except json.JSONDecodeError:
        items = []

    key_files = [f for f in items if isinstance(f, dict) and
                 (f.get("name", "").endswith((".py", ".md", ".toml", ".yaml", ".json")))]
    contents = {}
    for f in key_files[:5]:
        result = await tool_dispatcher._execute_one({
            "function": {"name": "github_read_file",
                          "arguments": f'{{"owner": "{owner}", "repo": "{repo}", "path": "{f["path"]}"}}'}
        })
        contents[f["path"]] = result.get("output", "")[:1000]

    return {"structure": {"items": items[:20]}, "key_files": contents}
