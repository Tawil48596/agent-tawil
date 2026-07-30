"""链式协作: A → B → C"""

from typing import Any, Callable


class ChainPattern:
    """链式协作模式 — 前一个输出作为后一个输入"""

    async def execute(self, tasks: list[dict], executor: Callable) -> list[dict]:
        results = []
        prev_output = ""
        for task in tasks:
            if prev_output:
                task["context"] = (task.get("context", "") + f"\n[上一步输出]\n{prev_output[:2000]}")
            result = await executor(task)
            results.append(result)
            prev_output = result.get("result", result.get("error", ""))
            if result.get("status") == "failed":
                break
        return results
