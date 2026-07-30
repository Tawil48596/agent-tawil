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

    def __init__(self, router: ModelRouter, agent_config: dict[str, Any]):
        self.router = router
        self.max_turns = agent_config.get("max_turns", 50)
        self.compression_threshold = agent_config.get("context_compression_threshold", 0.75)
        self.prompt_builder = PromptBuilder()
        self.context_manager = ContextManager()
        self.tool_dispatcher = ToolDispatcher()

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

        return await self._inference_loop(messages, route_result, enabled_tools)

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

        while turns < self.max_turns:
            # 上下文压缩检查
            if self.context_manager.needs_compression(messages, route_result.context_length):
                yield {"type": "compressing", "content": "压缩上下文中..."}
                messages = await self.context_manager.compress(messages, route_result)

            try:
                response = await acompletion(
                    model=self._litellm_model_name(route_result),
                    messages=messages,
                    tools=self._format_tools(enabled_tools) if enabled_tools else None,
                    api_key=route_result.api_key,
                    api_base=route_result.base_url if route_result.base_url else None,
                    stream=True,
                )

                # 收集流式响应
                full_text = ""
                tool_calls_buffer: dict[int, dict] = {}
                current_event_type = None

                async for chunk in response:
                    delta = chunk.choices[0].delta

                    # 文本 token
                    if delta.content:
                        full_text += delta.content
                        yield {"type": "text", "content": delta.content}

                    # 工具调用 token (流式累积)
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            idx = tc.index
                            if idx not in tool_calls_buffer:
                                tool_calls_buffer[idx] = {
                                    "id": tc.id or "",
                                    "function": {"name": "", "arguments": ""},
                                }
                            if tc.id:
                                tool_calls_buffer[idx]["id"] = tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_calls_buffer[idx]["function"]["name"] = tc.function.name
                                if tc.function.arguments:
                                    tool_calls_buffer[idx]["function"]["arguments"] += tc.function.arguments

                    # 结束
                    if chunk.choices[0].finish_reason == "stop":
                        if full_text:
                            yield {
                                "type": "done",
                                "content": full_text,
                                "stop_reason": "complete",
                                "model": route_result.model,
                                "provider": route_result.provider,
                            }
                        return

                    elif chunk.choices[0].finish_reason == "tool_calls":
                        # 执行工具调用
                        tool_calls_list = list(tool_calls_buffer.values())
                        yield {"type": "tool_calls", "calls": tool_calls_list, "status": "pending"}

                        results = await self.tool_dispatcher.execute_parallel(tool_calls_list)
                        yield {"type": "tool_results", "results": results}

                        # 将工具结果追加到消息
                        assistant_msg = {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": tool_calls_list,
                        }
                        messages.append(assistant_msg)

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
                        break  # 回到 while 循环继续推理

            except Exception as e:
                logger.error("LLM error", error=str(e))
                # 降级重试
                fallback = self.router.route(RouteRequest(
                    task_type=task_type,
                    prefer_fast=True,
                ))
                route_result = fallback
                consecutive_failures += 1
                if consecutive_failures > 2:
                    yield {"type": "error", "message": f"LLM 调用失败: {str(e)}"}
                    return

            turns += 1

        yield {"type": "done", "stop_reason": "max_turns", "content": "达到最大推理轮次。"}

    # ── 内部方法 ──

    async def _inference_loop(
        self, messages: list[dict], route_result: RouteResult, enabled_tools: Optional[list[dict]]
    ) -> EngineResponse:
        """非流式推理循环"""
        turns = 0
        consecutive_failures = 0

        while turns < self.max_turns:
            if self.context_manager.needs_compression(messages, route_result.context_length):
                messages = await self.context_manager.compress(messages, route_result)

            try:
                response = await acompletion(
                    model=self._litellm_model_name(route_result),
                    messages=messages,
                    tools=self._format_tools(enabled_tools) if enabled_tools else None,
                    api_key=route_result.api_key,
                    api_base=route_result.base_url if route_result.base_url else None,
                )
            except Exception as e:
                logger.error("LLM error", error=str(e))
                fallback = self.router.route(RouteRequest(task_type=TaskType.FAST))
                route_result = fallback
                consecutive_failures += 1
                if consecutive_failures > 2:
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
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                }
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
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in choice.message.tool_calls
            ]
            results = await self.tool_dispatcher.execute_parallel(tool_calls_raw)

            messages.append({
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": tool_calls_raw,
            })
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
