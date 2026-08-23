"""用量告警 — 超预算通知"""

import contextlib
from collections.abc import Callable


class BudgetAlerts:
    """预算告警"""

    def __init__(self, daily_budget: float = 50.0, monthly_budget: float = 500.0):
        self._daily = daily_budget
        self._monthly = monthly_budget
        self._handlers: list[Callable] = []

    def check(self, daily_cost: float, monthly_cost: float) -> list[dict]:
        alerts = []
        if daily_cost > self._daily:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"日预算超支: ${daily_cost:.2f} > ${self._daily:.2f}",
                }
            )
        if monthly_cost > self._monthly:
            alerts.append(
                {
                    "level": "critical",
                    "message": f"月预算超支: ${monthly_cost:.2f} > ${self._monthly:.2f}",
                }
            )
        if daily_cost > self._daily * 0.8:
            alerts.append(
                {"level": "info", "message": f"日预算使用 {(daily_cost / self._daily) * 100:.0f}%"}
            )
        for a in alerts:
            for h in self._handlers:
                with contextlib.suppress(BaseException):
                    h(a)
        return alerts

    def on_alert(self, handler: Callable):
        self._handlers.append(handler)
