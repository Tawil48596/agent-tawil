"""模型路由器 — 多 Provider 管理、任务路由、降级链、per-message 模型覆盖"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


class TaskType(str, Enum):
    REASONING = "reasoning"       # 通用推理
    CODING = "coding"             # 代码生成/审查
    SUMMARIZATION = "summarization"  # 摘要/压缩
    EMBEDDING = "embedding"       # 文本嵌入
    VISION = "vision"             # 图像理解
    FAST = "fast"                 # 快速响应 (小模型)


@dataclass
class ModelInfo:
    """模型元信息"""
    name: str                     # gpt-4o / claude-sonnet-4 / deepseek-v3
    provider: str                 # openai / anthropic / deepseek
    context_length: int
    supports_vision: bool = False
    supports_tools: bool = True
    supports_reasoning_effort: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    tags: set[str] = field(default_factory=set)  # reasoning, coding, fast, ...


@dataclass
class RouteRequest:
    """路由请求"""
    task_type: TaskType = TaskType.REASONING
    override_model: Optional[str] = None   # 用户强制指定模型 (per-message)
    prefer_provider: Optional[str] = None  # 用户偏好 Provider
    prefer_fast: bool = False
    prefer_vision: bool = False
    max_context_needed: int = 8192         # 需要的上下文长度


@dataclass
class RouteResult:
    """路由结果"""
    model: str
    provider: str
    api_key: str
    base_url: str
    context_length: int
    supports_vision: bool
    supports_tools: bool
    supports_reasoning_effort: bool
    routed_by: str  # "override" | "task" | "default" | "fallback"


class ModelRouter:
    """多模型路由器

    使用方式:
        router = ModelRouter(config)
        result = router.route(RouteRequest(
            task_type=TaskType.CODING,
            override_model="claude-sonnet-4",  # 用户可在消息级指定
        ))
        response = await router.chat(result, messages, tools)
    """

    def __init__(self, config: dict[str, Any]):
        self._providers: dict[str, dict[str, Any]] = {}
        self._models: dict[str, ModelInfo] = {}
        self._fallback_chain: list[str] = config.get("llm", {}).get("fallback_chain", [])
        self._default_model = config.get("llm", {}).get("default_model", "gpt-4o")
        self._fast_model = config.get("llm", {}).get("fast_model", "gpt-4o-mini")
        self._embedding_model = config.get("llm", {}).get("embedding_model", "text-embedding-3-small")
        self._task_map: dict[TaskType, str] = {}  # task_type → default model

        self._load_from_config(config)

    # ── Config loading ──

    def _load_from_config(self, config: dict[str, Any]):
        """从配置加载 Provider 和模型"""
        llm_cfg = config.get("llm", {})
        providers_cfg = llm_cfg.get("providers", {})

        for provider_name, provider_cfg in providers_cfg.items():
            api_key = provider_cfg.get("api_key", "")
            base_url = provider_cfg.get("base_url", "")
            self._providers[provider_name] = {
                "api_key": api_key,
                "base_url": base_url,
            }

        # 内置模型注册表
        self._register_model(ModelInfo(
            name="gpt-5.1", provider="openai",
            context_length=400000, supports_vision=True,
            supports_reasoning_effort=True,
            tags={"reasoning", "coding", "vision"},
        ))
        self._register_model(ModelInfo(
            name="gpt-5-mini", provider="openai",
            context_length=400000, supports_vision=True,
            supports_reasoning_effort=True,
            tags={"reasoning", "coding", "summarization", "fast"},
        ))
        self._register_model(ModelInfo(
            name="gpt-4o", provider="openai",
            context_length=128000, supports_vision=True,
            cost_per_1k_input=0.0025, cost_per_1k_output=0.01,
            tags={"reasoning", "coding", "vision", "fast"},
        ))
        self._register_model(ModelInfo(
            name="gpt-4o-mini", provider="openai",
            context_length=128000, supports_vision=True,
            cost_per_1k_input=0.00015, cost_per_1k_output=0.0006,
            tags={"reasoning", "summarization", "fast"},
        ))
        self._register_model(ModelInfo(
            name="claude-sonnet-4", provider="anthropic",
            context_length=200000, supports_vision=True,
            cost_per_1k_input=0.003, cost_per_1k_output=0.015,
            tags={"reasoning", "coding", "vision"},
        ))
        self._register_model(ModelInfo(
            name="claude-haiku-4-5", provider="anthropic",
            context_length=200000, supports_vision=True,
            cost_per_1k_input=0.0008, cost_per_1k_output=0.004,
            tags={"reasoning", "summarization", "fast"},
        ))
        self._register_model(ModelInfo(
            name="deepseek-v4-pro", provider="deepseek",
            context_length=1000000, supports_vision=False,
            supports_reasoning_effort=True,
            cost_per_1k_input=0.00014, cost_per_1k_output=0.00028,
            tags={"reasoning", "coding"},
        ))
        self._register_model(ModelInfo(
            name="deepseek-v4-flash", provider="deepseek",
            context_length=1000000, supports_vision=False,
            supports_reasoning_effort=True,
            tags={"reasoning", "coding", "summarization", "fast"},
        ))
        self._register_model(ModelInfo(
            name="text-embedding-3-small", provider="openai",
            context_length=8191, supports_vision=False, supports_tools=False,
            tags={"embedding"},
        ))

        # 任务 → 默认模型映射
        routing_cfg = llm_cfg.get("model_routing", {})
        self._task_map = {
            TaskType.REASONING: routing_cfg.get("reasoning", self._default_model),
            TaskType.CODING: routing_cfg.get("coding", self._default_model),
            TaskType.SUMMARIZATION: routing_cfg.get("summarization", self._fast_model),
            TaskType.EMBEDDING: routing_cfg.get("embedding", self._embedding_model),
            TaskType.VISION: routing_cfg.get("reasoning", self._default_model),
            TaskType.FAST: self._fast_model,
        }

    def _register_model(self, info: ModelInfo):
        self._models[info.name] = info

    @staticmethod
    def _has_usable_key(provider: dict[str, Any]) -> bool:
        api_key = str(provider.get("api_key", "")).strip()
        return bool(api_key) and not (api_key.startswith("${") and api_key.endswith("}"))

    def update_provider(self, name: str, *, api_key: str, base_url: str) -> None:
        """Update provider credentials for the running process."""
        self._providers[name] = {
            "api_key": api_key.strip(),
            "base_url": base_url.strip(),
        }

    def remove_provider(self, name: str) -> None:
        """Remove runtime credentials without exposing their previous value."""
        self._providers.pop(name, None)

    def provider_status(self) -> list[dict[str, Any]]:
        """Return non-sensitive provider state for the settings UI."""
        names = sorted(set(self._providers) | {model.provider for model in self._models.values()})
        return [
            {
                "name": name,
                "base_url": self._providers.get(name, {}).get("base_url", ""),
                "configured": self._has_usable_key(self._providers.get(name, {})),
            }
            for name in names
        ]

    # ── Public API ──

    def list_models(self) -> list[dict[str, Any]]:
        """列出所有可用模型（给 UI/CLI 展示）"""
        return [
            {
                "name": info.name,
                "provider": info.provider,
                "context_length": info.context_length,
                "supports_vision": info.supports_vision,
                "supports_tools": info.supports_tools,
                "supports_reasoning_effort": info.supports_reasoning_effort,
                "cost_per_1k_input": info.cost_per_1k_input,
                "cost_per_1k_output": info.cost_per_1k_output,
                "tags": sorted(info.tags),
                "available": self._has_usable_key(self._providers.get(info.provider, {})),
            }
            for info in self._models.values()
        ]

    def list_available_models(self) -> list[str]:
        """列出当前可用（已配置 API Key）的模型名"""
        return [
            name for name, info in self._models.items()
            if self._has_usable_key(self._providers.get(info.provider, {}))
        ]

    def route(self, request: RouteRequest) -> RouteResult:
        """路由模型选择

        优先级:
          1. override_model — 用户显式指定（per-message / 每轮对话）
          2. task_type + prefer_provider — 按任务类型 + Provider 偏好
          3. default_model — 全局默认
          4. fallback_chain — Provider 不可用时降级
        """
        # 1. 用户显式覆盖（per-message 切换）
        if request.override_model:
            model_info = self._models.get(request.override_model)
            if model_info and self._has_usable_key(self._providers.get(model_info.provider, {})):
                return self._build_result(model_info, "override")
            logger.warning("Override model not available", model=request.override_model)

        # 2. 按任务类型路由
        model_name = self._task_map.get(request.task_type, self._default_model)

        # 3. 偏好 Provider 调整
        if request.prefer_provider:
            candidate = self._find_model_by_provider(request.task_type, request.prefer_provider)
            if candidate:
                model_name = candidate

        # 4. 视觉需求
        if request.prefer_vision:
            vision_model = self._find_vision_model()
            if vision_model:
                model_name = vision_model

        # 5. 快速响应
        if request.prefer_fast:
            model_name = self._fast_model

        model_info = self._models.get(model_name)
        if model_info and self._has_usable_key(self._providers.get(model_info.provider, {})):
            return self._build_result(model_info, "task")

        # 6. 降级链
        for provider_name in self._fallback_chain:
            if self._has_usable_key(self._providers.get(provider_name, {})):
                fallback_model = self._find_model_by_provider(request.task_type, provider_name)
                if fallback_model:
                    model_info = self._models[fallback_model]
                    logger.info("Using fallback", provider=provider_name, model=model_info.name)
                    return self._build_result(model_info, "fallback")

        raise RuntimeError("No available LLM provider. Check API keys in config.")

    def get_model_for_task(self, task_type: TaskType) -> str:
        """快速获取任务对应的模型名"""
        return self._task_map.get(task_type, self._default_model)

    # ── Helpers ──

    def _build_result(self, info: ModelInfo, routed_by: str) -> RouteResult:
        provider_cfg = self._providers[info.provider]
        return RouteResult(
            model=info.name,
            provider=info.provider,
            api_key=provider_cfg["api_key"],
            base_url=provider_cfg["base_url"],
            context_length=info.context_length,
            supports_vision=info.supports_vision,
            supports_tools=info.supports_tools,
            supports_reasoning_effort=info.supports_reasoning_effort,
            routed_by=routed_by,
        )

    def _find_model_by_provider(self, task_type: TaskType, provider: str) -> Optional[str]:
        """在指定 Provider 下找适合任务的模型"""
        for name, info in self._models.items():
            if info.provider == provider and self._has_usable_key(self._providers.get(provider, {})):
                # 检查标签匹配
                if task_type.value in info.tags:
                    return name
        # 退而求其次
        for name, info in self._models.items():
            if info.provider == provider and self._has_usable_key(self._providers.get(provider, {})):
                return name
        return None

    def _find_vision_model(self) -> Optional[str]:
        for name, info in self._models.items():
            if info.supports_vision and self._has_usable_key(self._providers.get(info.provider, {})):
                return name
        return None
