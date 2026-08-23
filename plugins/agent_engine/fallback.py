"""模型降级 — 主模型不可用时切换到备用"""

from plugins.agent_engine.model_router import ModelRouter, RouteRequest, RouteResult, TaskType


class FallbackHandler:
    """模型降级处理器"""

    def __init__(self, router: ModelRouter, fallback_chain: list[str]):
        self.router = router
        self._chain = fallback_chain  # ["openai", "anthropic", "deepseek"]
        self._failed_providers: set[str] = set()
        self._provider_index = 0

    def get_next(self, failed_result: RouteResult | None = None) -> RouteResult | None:
        """获取下一个可用的 Provider 模型"""
        if failed_result:
            self._failed_providers.add(failed_result.provider)

        for provider in self._chain:
            if provider not in self._failed_providers:
                try:
                    return self.router.route(
                        RouteRequest(
                            task_type=TaskType.REASONING,
                            prefer_provider=provider,
                            excluded_providers=set(self._failed_providers),
                        )
                    )
                except RuntimeError:
                    self._failed_providers.add(provider)

        return None

    def reset(self):
        """重置失败记录 (定期清)"""
        self._failed_providers.clear()

    @property
    def all_failed(self) -> bool:
        return len(self._failed_providers) >= len(self._chain)
