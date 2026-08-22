"""健康检查器"""

import asyncio
import inspect
from typing import Any, Callable


class HealthChecker:
    def __init__(self):
        self._checks: dict[str, Callable] = {}

    def register(self, name: str, check_fn: Callable): self._checks[name] = check_fn

    async def check_all(self) -> dict:
        results = {}
        for name, fn in self._checks.items():
            try:
                import asyncio
                if inspect.iscoroutinefunction(fn):
                    ok = await fn()
                else:
                    ok = fn()
                results[name] = "ok" if ok else "unhealthy"
            except Exception as e:
                results[name] = f"error: {e}"
        return {"status": "ok" if all(v == "ok" for v in results.values()) else "degraded", "checks": results}
