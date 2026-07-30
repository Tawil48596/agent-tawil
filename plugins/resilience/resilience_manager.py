"""服务降级与熔断器 — 三级降级 + 自动恢复"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional


class CircuitState(str, Enum):
    CLOSED = "closed"          # 正常
    HALF_OPEN = "half_open"    # 半开 (试探)
    OPEN = "open"              # 熔断


@dataclass
class CircuitBreaker:
    """熔断器"""
    name: str
    failure_threshold: int = 5      # 连续失败 N 次 → 熔断
    recovery_timeout: int = 30      # 熔断后 N 秒 → 半开
    half_open_max_requests: int = 2 # 半开时允许的试探请求数

    _state: CircuitState = CircuitState.CLOSED
    _failure_count: int = 0
    _last_failure_time: float = 0.0
    _half_open_requests: int = 0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_requests = 0
        return self._state

    def success(self):
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_requests += 1
            if self._half_open_requests >= self.half_open_max_requests:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        else:
            self._failure_count = 0

    def failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN


class DegradationLevel(str, Enum):
    NONE = "none"            # 无降级
    L1_MODEL = "l1_model"    # 模型降级 (切换备用 Provider)
    L2_TOOL = "l2_tool"      # 工具降级 (本地快照模式)
    L3_RETRIEVAL = "l3_retrieval"  # 检索降级 (向量 → BM25)


@dataclass
class DegradationResult:
    level: DegradationLevel
    original_error: Optional[str] = None
    degraded: bool = False
    message: str = ""


class ResilienceManager:
    """韧性管理器 — 三级降级 + 熔断器"""

    def __init__(self, config: dict = None):
        cfg = config or {}
        resilience_cfg = cfg.get("resilience", {}) if isinstance(cfg, dict) else {}

        self._circuits: dict[str, CircuitBreaker] = {}
        for name in ["github_mcp", "web_search", "embedding", "reranker"]:
            self._circuits[name] = CircuitBreaker(name=name)

    def get_circuit(self, name: str) -> CircuitBreaker:
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name=name)
        return self._circuits[name]

    async def call_with_degradation(
        self,
        primary: Callable,
        fallback: Optional[Callable] = None,
        circuit_name: str = "",
        degradation_level: DegradationLevel = DegradationLevel.L2_TOOL,
    ) -> DegradationResult:
        """执行主逻辑，失败时降级到 fallback"""
        circuit = self._circuits.get(circuit_name)

        # 熔断中 → 直接降级
        if circuit and circuit.state == CircuitState.OPEN:
            if fallback:
                try:
                    result = await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
                    return DegradationResult(
                        level=degradation_level, degraded=True,
                        message=f"熔断中，已降级 ({circuit_name})",
                    )
                except Exception:
                    pass
            return DegradationResult(
                level=degradation_level, degraded=True,
                message=f"服务不可用 ({circuit_name})",
            )

        # 尝试主逻辑
        try:
            result = await primary() if asyncio.iscoroutinefunction(primary) else primary()
            if circuit:
                circuit.success()
            return DegradationResult(level=DegradationLevel.NONE)
        except Exception as e:
            if circuit:
                circuit.failure()

            if fallback:
                try:
                    result = await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
                    return DegradationResult(
                        level=degradation_level, degraded=True,
                        original_error=str(e),
                        message=f"已降级 ({degradation_level.value})",
                    )
                except Exception as fb_e:
                    return DegradationResult(
                        level=degradation_level, degraded=True,
                        original_error=str(e),
                    )

            return DegradationResult(
                level=degradation_level, degraded=True,
                original_error=str(e),
            )

    def wrap(self, circuit_name: str):
        """装饰器: 自动熔断保护"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                circuit = self.get_circuit(circuit_name)
                if circuit.state == CircuitState.OPEN:
                    raise ServiceUnavailableError(f"Circuit OPEN: {circuit_name}")
                try:
                    result = await func(*args, **kwargs)
                    circuit.success()
                    return result
                except Exception as e:
                    circuit.failure()
                    raise
            return wrapper
        return decorator


class ServiceUnavailableError(Exception):
    pass
