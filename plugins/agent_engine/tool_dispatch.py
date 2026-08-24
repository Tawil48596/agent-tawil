"""工具调度器 — 工具调用解析与并行分发"""

import asyncio
import inspect
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog

logger = structlog.get_logger()


class ToolDispatcher:
    """工具调用调度器

    支持:
    - 无依赖工具的并行执行
    - 工具注册表查询
    - 执行超时保护
    """

    def __init__(
        self,
        timeout: float = 30.0,
        approval_handler: Callable[[str, dict[str, Any], dict[str, Any]], bool | Awaitable[bool]]
        | None = None,
    ):
        self._registry: dict[str, Any] = {}  # tool_name → handler
        self._approval_required: set[str] = set()
        self._approval_handler = approval_handler
        self._audit_handler: Callable[..., Any] | None = None
        self._execution_handler: Callable[[str], Any] | None = None
        self._execution_ledger: Any | None = None
        self._timeout = timeout

    def register(self, name: str, handler: Any, *, requires_approval: bool = False):
        """注册工具处理器"""
        self._registry[name] = handler
        if requires_approval:
            self._approval_required.add(name)
        else:
            self._approval_required.discard(name)

    def set_approval_handler(
        self,
        handler: Callable[[str, dict[str, Any], dict[str, Any]], bool | Awaitable[bool]] | None,
    ) -> None:
        """Bind an application-owned approval decision provider."""
        self._approval_handler = handler

    def set_audit_handler(self, handler: Callable[..., Any] | None) -> None:
        self._audit_handler = handler

    def set_execution_handler(self, handler: Callable[[str], Any] | None) -> None:
        """Observe real handler executions without coupling the dispatcher to a registry."""
        self._execution_handler = handler

    def set_execution_ledger(self, ledger: Any | None) -> None:
        """Bind durable storage for completed tool-call results."""
        self._execution_ledger = ledger

    def _audit(self, event_type: str, **fields: Any) -> None:
        if self._audit_handler is None:
            return
        try:
            self._audit_handler(event_type, **fields)
        except Exception:
            logger.warning("Audit handler failed", event_type=event_type)

    def _record_execution(self, name: str) -> None:
        if self._execution_handler is None:
            return
        try:
            self._execution_handler(name)
        except Exception:
            logger.warning("Execution handler failed", tool=name)

    def unregister(self, name: str):
        """注销工具"""
        self._registry.pop(name, None)
        self._approval_required.discard(name)

    def list_tools(self) -> list[str]:
        """列出已注册的工具名"""
        return list(self._registry.keys())

    async def execute_parallel(
        self, tool_calls: list[dict], *, context: dict[str, Any] | None = None
    ) -> list[dict]:
        """并行执行一组工具调用 (假设它们之间无依赖)"""
        if not tool_calls:
            return []

        tasks = [self._execute_one(tc, context=context) for tc in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        formatted = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted.append(
                    {
                        "index": i,
                        "name": tool_calls[i].get("function", {}).get("name", "unknown"),
                        "output": str(result),
                        "error": True,
                    }
                )
            else:
                formatted.append(result)
        return formatted

    async def execute_sequential(
        self, tool_calls: list[dict], *, context: dict[str, Any] | None = None
    ) -> list[dict]:
        """串行执行工具调用 (有依赖关系时)"""
        results = []
        for tc in tool_calls:
            try:
                result = await self._execute_one(tc, context=context)
                results.append(result)
            except Exception as e:
                results.append(
                    {
                        "name": tc.get("function", {}).get("name", "unknown"),
                        "output": str(e),
                        "error": True,
                    }
                )
        return results

    async def _execute_one(self, tool_call: dict, *, context: dict[str, Any] | None = None) -> dict:
        """执行单个工具调用"""
        func = tool_call.get("function", {})
        name = func.get("name", "")
        args_str = func.get("arguments", "{}")

        # 参数可能是 JSON 字符串
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else args_str
        except json.JSONDecodeError as error:
            return {
                "name": name,
                "output": f"错误: 工具参数不是有效 JSON: {error.msg}",
                "error": True,
            }
        if not isinstance(args, dict):
            return {
                "name": name,
                "output": "错误: 工具参数必须是 JSON 对象",
                "error": True,
            }

        logger.info("Executing tool", name=name, argument_names=sorted(args))

        handler = self._registry.get(name)
        if handler is None:
            return {
                "name": name,
                "output": f"错误: 工具 '{name}' 未注册。可用工具: {list(self._registry.keys())}",
                "error": True,
            }

        if name in self._approval_required:
            if self._approval_handler is None:
                self._audit("tool.approval_required", tool=name, context=context or {})
                return {
                    "name": name,
                    "output": f"错误: 工具 '{name}' 需要外部审批",
                    "error": True,
                    "code": "approval_required",
                }
            decision = self._approval_handler(name, args, context or {})
            approved = await decision if inspect.isawaitable(decision) else decision
            if approved is not True:
                self._audit("tool.approval_denied", tool=name, context=context or {})
                return {
                    "name": name,
                    "output": f"错误: 工具 '{name}' 的审批被拒绝",
                    "error": True,
                    "code": "approval_denied",
                }

            self._audit("tool.approval_approved", tool=name, context=context or {})

        session_id = str((context or {}).get("id", ""))
        call_id = str(tool_call.get("id", ""))
        attempt_id = ""
        if self._execution_ledger is not None:
            decision = self._execution_ledger.acquire(session_id, call_id, name, args)
            if decision["action"] == "replay":
                replayed = decision["result"]
                replayed["replayed"] = True
                self._audit("tool.replayed", tool=name, context=context or {})
                return replayed
            if decision["action"] != "execute":
                code = {
                    "busy": "tool_in_progress",
                    "uncertain": "tool_execution_uncertain",
                    "conflict": "tool_call_conflict",
                }[decision["action"]]
                return {"name": name, "output": f"错误: {code}", "error": True, "code": code}
            attempt_id = decision["attempt_id"]

        started = time.monotonic()
        self._record_execution(name)
        self._audit("tool.started", tool=name, arguments=args, context=context or {})
        try:
            output = await asyncio.wait_for(
                handler(**args)
                if inspect.iscoroutinefunction(handler)
                else _run_sync(handler, **args),
                timeout=self._timeout,
            )
            if isinstance(output, str):
                output_text = output
            elif isinstance(output, (dict, list)):
                output_text = json.dumps(output, ensure_ascii=False, default=str)
            else:
                output_text = str(output)

            structured_error = isinstance(output, dict) and bool(output.get("error"))
            if isinstance(output, str):
                try:
                    payload = json.loads(output)
                    structured_error = isinstance(payload, dict) and bool(payload.get("error"))
                except json.JSONDecodeError:
                    pass
            result = {
                "name": name,
                "output": output_text,
                "error": structured_error,
            }
            self._audit(
                "tool.completed",
                tool=name,
                error=structured_error,
                duration_ms=round((time.monotonic() - started) * 1000, 2),
                output_length=len(output_text),
                context=context or {},
            )
            if self._execution_ledger is not None:
                if structured_error:
                    self._execution_ledger.release(session_id, call_id, attempt_id)
                else:
                    self._execution_ledger.store(session_id, call_id, name, args, result)
            return result
        except TimeoutError:
            if self._execution_ledger is not None:
                self._execution_ledger.mark_uncertain(
                    session_id, call_id, attempt_id, "execution_timeout"
                )
            self._audit("tool.timeout", tool=name, context=context or {})
            return {
                "name": name,
                "output": f"错误: 工具 '{name}' 执行超时 ({self._timeout}s)",
                "error": True,
            }
        except Exception as e:
            if self._execution_ledger is not None:
                self._execution_ledger.mark_uncertain(
                    session_id, call_id, attempt_id, "execution_failed"
                )
            self._audit(
                "tool.failed", tool=name, error_type=type(e).__name__, context=context or {}
            )
            logger.warning("Tool execution failed", name=name, error=str(e))
            return {
                "name": name,
                "output": f"错误: {str(e)}",
                "error": True,
            }


async def _run_sync(func, **kwargs):
    """在线程池中运行同步函数"""
    return await asyncio.to_thread(func, **kwargs)
