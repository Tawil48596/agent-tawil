"""Deterministic LiteLLM-compatible response source for offline agent evals."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any


@dataclass
class ScriptedResponse:
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    reasoning_content: str = ""
    usage: dict[str, int] = field(
        default_factory=lambda: {
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        }
    )


class ScriptedLLM:
    """Replay finite responses while recording every completion request."""

    def __init__(self, responses: list[ScriptedResponse]):
        self._responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        if not self._responses:
            raise RuntimeError("Scripted LLM response queue exhausted")
        response = self._responses.pop(0)
        if kwargs.get("stream"):
            return self._stream(response)
        return self._completion(response)

    @staticmethod
    def _tool_calls(items: list[dict[str, Any]], *, streaming: bool) -> list[Any]:
        calls = []
        for index, item in enumerate(items):
            function = item.get("function", item)
            calls.append(
                SimpleNamespace(
                    index=index if streaming else None,
                    id=item.get("id", f"call_{index + 1}"),
                    type=item.get("type", "function"),
                    function=SimpleNamespace(
                        name=function["name"],
                        arguments=function.get("arguments", "{}"),
                    ),
                )
            )
        return calls

    @classmethod
    def _completion(cls, response: ScriptedResponse) -> Any:
        tool_calls = cls._tool_calls(response.tool_calls, streaming=False)
        message = SimpleNamespace(
            content=response.content,
            reasoning_content=response.reasoning_content or None,
            tool_calls=tool_calls,
        )
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=message,
                    finish_reason="tool_calls" if tool_calls else "stop",
                )
            ],
            usage=response.usage,
        )

    @classmethod
    async def _stream(cls, response: ScriptedResponse) -> AsyncIterator[Any]:
        tool_calls = cls._tool_calls(response.tool_calls, streaming=True)
        yield SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(
                        content=response.content or None,
                        reasoning_content=response.reasoning_content or None,
                        tool_calls=tool_calls or None,
                    ),
                    finish_reason="tool_calls" if tool_calls else "stop",
                )
            ],
            usage=response.usage,
        )
