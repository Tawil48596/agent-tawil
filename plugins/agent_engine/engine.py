"""Agent 推理引擎 — 核心循环 (observe → think → act → observe)"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator, Optional

import structlog
from litellm import acompletion

from plugins.agent_engine.model_router import ModelRouter, RouteRequest, RouteResult, TaskType
from plugins.agent_engine.prompt_builder import PromptBuilder
from plugins.agent_engine.context_manager import ContextManager
from plugins.agent_engine.tool_dispatch import ToolDispatcher
from shared.models import ToolCall

logger = structlog.get_logger()


@dataclass
class EngineResponse:
    text: str
    stop_reason: str = "complete"  # complete | max_turns | tool_error | content_filter | timeout
    model_used: str = ""
    provider_used: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class AgentEngine:
    """主推理引擎"""

    def __init__(
        self,
        router: ModelRouter,
        agent_config: dict[str, Any],
        tool_dispatcher: Optional[ToolDispatcher] = None,
    ):
        self.router = router
        self.max_turns = agent_config.get("max_turns", 50)
        self.compression_threshold = agent_config.get("context_compression_threshold", 0.75)
        self.prompt_builder = PromptBuilder()
        self.context_manager = ContextManager()
        self.tool_dispatcher = tool_dispatcher or ToolDispatcher()

    # ── 同步运行 ──

    async def run(
        self,
        user_message: str,
        *,
        session: Optional[dict] = None,
        history: Optional[list[dict]] = None,
        memories: Optional[list[dict]] = None,
        rag_context: Optional[list[dict]] = None,
        enabled_tools: Optional[list[dict]] = None,
        override_model: Optional[str] = None,
        task_type: TaskType = TaskType.REASONING,
        reasoning_effort: Optional[str] = None,
        skill_files: Optional[list[str]] = None,
    ) -> EngineResponse:
        """运行 Agent 推理循环，返回最终回复"""
        messages = await self._build_initial_messages(
            user_message, session, history, memories, rag_context,
            enabled_tools, skill_files,
        )

        route_result = self.router.route(RouteRequest(
            task_type=task_type,
            override_model=override_model,
        ))

        return await self._inference_loop(
            messages, route_result, enabled_tools, reasoning_effort, session
        )

    # ── 流式运行 ──

    async def run_stream(
        self,
        user_message: str,
        *,
        session: Optional[dict] = None,
        history: Optional[list[dict]] = None,
        memories: Optional[list[dict]] = None,
        rag_context: Optional[list[dict]] = None,
        enabled_tools: Optional[list[dict]] = None,
        override_model: Optional[str] = None,
        task_type: TaskType = TaskType.REASONING,
        reasoning_effort: Optional[str] = None,
        skill_files: Optional[list[str]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """流式运行 Agent 推理循环，逐 token 产出事件"""
        messages = await self._build_initial_messages(
            user_message, session, history, memories, rag_context,
            enabled_tools, skill_files,
        )

        route_result = self.router.route(RouteRequest(
            task_type=task_type,
            override_model=override_model,
        ))

        turns = 0
        consecutive_failures = 0
        failed_providers: set[str] = set()
        total_usage = self._empty_usage()

        while turns < self.max_turns:
            # 上下文压缩检查
            if self.context_manager.needs_compression(messages, route_result.context_length):
                yield {"type": "compressing", "content": "压缩上下文中..."}
                messages = await self.context_manager.compress(messages, route_result)

            try:
                completion_kwargs = self._completion_kwargs(
                    route_result, messages, enabled_tools, reasoning_effort
                )
                response = await acompletion(
                    stream=True,
                    stream_options={"include_usage": True},
                    **completion_kwargs,
                )

                full_text = ""
                reasoning_content = ""
                tool_calls_buffer: dict[int, dict] = {}
                finish_reason = None
                turn_usage = self._empty_usage()

                async for chunk in response:
                    chunk_usage = self._normalize_usage(getattr(chunk, "usage", None))
                    if chunk_usage["requests"]:
                        turn_usage = chunk_usage

                    choices = getattr(chunk, "choices", None) or []
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.delta

                    if delta.content:
                        full_text += delta.content
                        yield {"type": "text", "content": delta.content}

                    reasoning_piece = self._reasoning_content(delta)
                    if reasoning_piece:
                        reasoning_content += reasoning_piece

                    delta_tool_calls = getattr(delta, "tool_calls", None)
                    if delta_tool_calls:
                        for tc in delta_tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_buffer:
                                tool_calls_buffer[idx] = {
                                    "id": tc.id or "",
                                    "type": getattr(tc, "type", None) or "function",
                                    "function": {"name": "", "arguments": ""},
                                }
                            if tc.id:
                                tool_calls_buffer[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls_buffer[idx]["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls_buffer[idx]["function"]["arguments"] += tc.function.arguments

                    if choice.finish_reason:
                        finish_reason = choice.finish_reason

                total_usage = self._add_usage(total_usage, turn_usage)

                if finish_reason == "stop":
                    yield {
                        "type": "done",
                        "content": full_text,
                        "stop_reason": "complete",
                        "model": route_result.model,
                        "provider": route_result.provider,
                        "usage": total_usage,
                    }
                    return

                if finish_reason == "tool_calls":
                    tool_calls_list = list(tool_calls_buffer.values())
                    yield {"type": "tool_calls", "calls": tool_calls_list, "status": "pending"}

                    results = await self.tool_dispatcher.execute_parallel(
                        tool_calls_list, context=session
                    )
                    yield {"type": "tool_results", "results": results}
                    assistant_message = {
                        "role": "assistant",
                        "content": full_text or "",
                        "tool_calls": tool_calls_list,
                    }
                    if reasoning_content:
                        assistant_message["reasoning_content"] = reasoning_content
                    messages.append(assistant_message)
                    for i, result in enumerate(results):
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_calls_list[i].get("id", ""),
                            "content": result.get("output", ""),
                        })

                    if all(r.get("error") for r in results):
                        consecutive_failures += 1
                        if consecutive_failures > 3:
                            yield {
                                "type": "error",
                                "message": "工具调用连续失败。",
                                "code": "tool_error",
                            }
                            return
                    else:
                        consecutive_failures = 0

            except Exception as e:
                failed_provider = route_result.provider
                failed_providers.add(failed_provider)
                logger.error(
                    "LLM error",
                    error=str(e),
                    provider=failed_provider,
                    model=route_result.model,
                )
                consecutive_failures += 1
                try:
                    route_result = self.router.route(RouteRequest(
                        task_type=task_type,
                        excluded_providers=failed_providers,
                    ))
                except RuntimeError:
                    yield {"type": "error", "message": f"LLM 调用失败: {str(e)}"}
                    return

            turns += 1

        yield {"type": "done", "stop_reason": "max_turns", "content": "达到最大推理轮次。"}

    # ── 内部方法 ──

    async def _inference_loop(
        self,
        messages: list[dict],
        route_result: RouteResult,
        enabled_tools: Optional[list[dict]],
        reasoning_effort: Optional[str] = None,
        session: Optional[dict] = None,
    ) -> EngineResponse:
        """非流式推理循环"""
        turns = 0
        consecutive_failures = 0
        failed_providers: set[str] = set()

        while turns < self.max_turns:
            if self.context_manager.needs_compression(messages, route_result.context_length):
                messages = await self.context_manager.compress(messages, route_result)

            try:
                response = await acompletion(**self._completion_kwargs(
                    route_result, messages, enabled_tools, reasoning_effort
                ))
            except Exception as e:
                failed_provider = route_result.provider
                failed_providers.add(failed_provider)
                logger.error(
                    "LLM error",
                    error=str(e),
                    provider=failed_provider,
                    model=route_result.model,
                )
                consecutive_failures += 1
                try:
                    route_result = self.router.route(RouteRequest(
                        task_type=TaskType.FAST,
                        excluded_providers=failed_providers,
                    ))
                except RuntimeError:
                    return EngineResponse(
                        text=f"LLM 调用失败: {str(e)}",
                        stop_reason="tool_error",
                        model_used=route_result.model,
                        provider_used=route_result.provider,
                    )
                continue

            choice = response.choices[0]
            finish_reason = choice.finish_reason

            if finish_reason == "stop" or not choice.message.tool_calls:
                usage = self._normalize_usage(getattr(response, "usage", None))
                return EngineResponse(
                    text=choice.message.content or "",
                    stop_reason="complete",
                    model_used=route_result.model,
                    provider_used=route_result.provider,
                    usage=usage,
                )

            # 工具调用
            tool_calls_raw = [
                {
                    "id": tc.id,
                    "type": getattr(tc, "type", None) or "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in choice.message.tool_calls
            ]
            results = await self.tool_dispatcher.execute_parallel(
                tool_calls_raw, context=session
            )

            assistant_message = {
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": tool_calls_raw,
            }
            reasoning_content = self._reasoning_content(choice.message)
            if reasoning_content:
                assistant_message["reasoning_content"] = reasoning_content
            messages.append(assistant_message)
            for i, result in enumerate(results):
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_calls_raw[i].get("id", ""),
                    "content": result.get("output", ""),
                })

            if all(r.get("error") for r in results):
                consecutive_failures += 1
                if consecutive_failures > 3:
                    return EngineResponse(
                        text="工具调用连续失败，请检查配置。",
                        stop_reason="tool_error",
                        model_used=route_result.model,
                        provider_used=route_result.provider,
                    )
            else:
                consecutive_failures = 0

            turns += 1

        return EngineResponse(
            text="达到最大推理轮次。",
            stop_reason="max_turns",
            model_used=route_result.model,
            provider_used=route_result.provider,
        )

    async def _build_initial_messages(
        self, user_message, session, history, memories, rag_context, enabled_tools, skill_files,
    ) -> list[dict]:
        system_prompt = self.prompt_builder.build_system_prompt(
            session=session,
            memories=memories,
            rag_context=rag_context,
            enabled_tools=enabled_tools,
            skill_files=skill_files,
        )

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})
        return messages

    @staticmethod
    def _litellm_model_name(route: RouteResult) -> str:
        """构建 LiteLLM 模型名 (provider/model)"""
        provider = route.provider
        model = route.model
        if provider == "openai":
            return model  # LiteLLM 原生支持
        return f"{provider}/{model}"

    def _completion_kwargs(
        self,
        route: RouteResult,
        messages: list[dict],
        tools: Optional[list[dict]],
        reasoning_effort: Optional[str],
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._litellm_model_name(route),
            "messages": messages,
            "api_key": route.api_key,
            "api_base": route.base_url if route.base_url else None,
        }
        formatted_tools = self._format_tools(tools) if route.supports_tools else None
        if formatted_tools:
            kwargs["tools"] = formatted_tools
            if route.provider != "deepseek":
                kwargs["tool_choice"] = "auto"
        if route.supports_reasoning_effort and reasoning_effort in {"low", "medium", "high"}:
            kwargs["reasoning_effort"] = reasoning_effort
        return kwargs

    @staticmethod
    def _reasoning_content(message: Any) -> str:
        value = getattr(message, "reasoning_content", None)
        if value is None:
            model_extra = getattr(message, "model_extra", None)
            if isinstance(model_extra, dict):
                value = model_extra.get("reasoning_content")
        return value or ""

    @staticmethod
    def _usage_value(source: Any, *names: str) -> int:
        if source is None:
            return 0
        for name in names:
            value = source.get(name) if isinstance(source, dict) else getattr(source, name, None)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    continue
        return 0

    @classmethod
    def _normalize_usage(cls, usage: Any) -> dict[str, int]:
        if usage is None:
            return cls._empty_usage()
        input_details = (
            usage.get("prompt_tokens_details") or usage.get("input_tokens_details")
            if isinstance(usage, dict)
            else getattr(usage, "prompt_tokens_details", None)
            or getattr(usage, "input_tokens_details", None)
        )
        output_details = (
            usage.get("completion_tokens_details") or usage.get("output_tokens_details")
            if isinstance(usage, dict)
            else getattr(usage, "completion_tokens_details", None)
            or getattr(usage, "output_tokens_details", None)
        )
        input_tokens = cls._usage_value(usage, "prompt_tokens", "input_tokens")
        output_tokens = cls._usage_value(usage, "completion_tokens", "output_tokens")
        total_tokens = cls._usage_value(usage, "total_tokens") or input_tokens + output_tokens
        return {
            "input_tokens": input_tokens,
            "cached_input_tokens": (
                cls._usage_value(input_details, "cached_tokens", "cache_read_tokens")
                or cls._usage_value(usage, "cache_read_input_tokens", "cached_input_tokens")
            ),
            "cache_write_input_tokens": (
                cls._usage_value(input_details, "cache_write_tokens", "cache_creation_tokens")
                or cls._usage_value(usage, "cache_creation_input_tokens")
            ),
            "output_tokens": output_tokens,
            "reasoning_tokens": cls._usage_value(output_details, "reasoning_tokens"),
            "total_tokens": total_tokens,
            "requests": 1,
        }

    @staticmethod
    def _empty_usage() -> dict[str, int]:
        return {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "output_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
        }

    @classmethod
    def _add_usage(cls, total: dict[str, int], addition: dict[str, int]) -> dict[str, int]:
        return {
            key: total.get(key, 0) + addition.get(key, 0)
            for key in cls._empty_usage()
        }

    @staticmethod
    def _format_tools(tools: Optional[list[dict]]) -> Optional[list[dict]]:
        """将工具定义转为 OpenAI function-calling 格式"""
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {"type": "object", "properties": {}, "required": []}),
                },
            }
            for t in tools
        ]
