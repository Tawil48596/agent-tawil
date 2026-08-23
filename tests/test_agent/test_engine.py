"""Test Agent Engine"""

from types import SimpleNamespace

import pytest


def test_model_router_initialization():
    from plugins.agent_engine.model_router import ModelRouter

    config = {
        "llm": {
            "default_model": "gpt-4o",
            "fast_model": "gpt-4o-mini",
            "providers": {"openai": {"api_key": "test", "base_url": ""}},
            "model_routing": {},
            "fallback_chain": ["openai"],
        },
        "agent": {"max_turns": 10},
    }
    router = ModelRouter(config)
    assert router._default_model == "gpt-4o"
    models = router.list_available_models()
    assert len(models) >= 1


def test_route_override():
    from plugins.agent_engine.model_router import ModelRouter, RouteRequest

    config = {
        "llm": {
            "default_model": "gpt-4o",
            "fast_model": "gpt-4o-mini",
            "providers": {"openai": {"api_key": "test", "base_url": ""}},
            "model_routing": {},
            "fallback_chain": ["openai"],
        },
        "agent": {"max_turns": 10},
    }
    router = ModelRouter(config)
    result = router.route(RouteRequest(override_model="gpt-4o"))
    assert result.routed_by == "override"
    assert result.model == "gpt-4o"


def test_task_routing():
    from plugins.agent_engine.model_router import ModelRouter, RouteRequest, TaskType

    config = {
        "llm": {
            "default_model": "gpt-4o",
            "fast_model": "gpt-4o-mini",
            "providers": {"openai": {"api_key": "test", "base_url": ""}},
            "model_routing": {"summarization": "gpt-4o-mini"},
            "fallback_chain": ["openai"],
        },
        "agent": {"max_turns": 10},
    }
    router = ModelRouter(config)
    result = router.route(RouteRequest(task_type=TaskType.SUMMARIZATION))
    assert result.routed_by == "task"
    assert result.model == "gpt-4o-mini"


def test_prompt_builder():
    from plugins.agent_engine.prompt_builder import PromptBuilder

    pb = PromptBuilder()
    prompt = pb.build_system_prompt(
        session={"id": "test", "title": "Test"},
        memories=[{"type": "preference", "content": "User likes Python"}],
        enabled_tools=[{"name": "echo", "description": "Echo tool"}],
    )
    assert "Python" in prompt
    assert "echo" in prompt


def test_context_manager():
    from plugins.agent_engine.context_manager import ContextManager

    cm = ContextManager()
    msgs = [{"role": "user", "content": "Hello world " * 10}]
    tokens = cm.count_tokens(msgs)
    assert tokens > 0


def test_engine_uses_shared_tool_dispatcher():
    from plugins.agent_engine.engine import AgentEngine
    from plugins.agent_engine.model_router import ModelRouter
    from plugins.agent_engine.tool_dispatch import ToolDispatcher

    config = {
        "llm": {
            "providers": {"openai": {"api_key": "test", "base_url": ""}},
            "fallback_chain": ["openai"],
        },
        "agent": {},
    }
    dispatcher = ToolDispatcher()
    engine = AgentEngine(ModelRouter(config), {}, dispatcher)

    assert engine.tool_dispatcher is dispatcher


def test_completion_kwargs_include_tools_and_supported_reasoning_effort():
    from plugins.agent_engine.engine import AgentEngine
    from plugins.agent_engine.model_router import ModelRouter, RouteRequest

    config = {
        "llm": {
            "providers": {"openai": {"api_key": "test", "base_url": ""}},
            "fallback_chain": ["openai"],
        },
        "agent": {},
    }
    router = ModelRouter(config)
    engine = AgentEngine(router, {})
    route = router.route(RouteRequest(override_model="gpt-5.1"))
    kwargs = engine._completion_kwargs(
        route,
        [{"role": "user", "content": "What time is it?"}],
        [
            {
                "name": "get_current_time",
                "description": "Get the current time",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
        "high",
    )

    assert kwargs["reasoning_effort"] == "high"
    assert kwargs["tool_choice"] == "auto"
    assert kwargs["tools"][0]["function"]["name"] == "get_current_time"


def test_reasoning_effort_is_ignored_for_unsupported_model():
    from plugins.agent_engine.engine import AgentEngine
    from plugins.agent_engine.model_router import ModelRouter, RouteRequest

    config = {
        "llm": {
            "providers": {"openai": {"api_key": "test", "base_url": ""}},
            "fallback_chain": ["openai"],
        },
        "agent": {},
    }
    router = ModelRouter(config)
    engine = AgentEngine(router, {})
    route = router.route(RouteRequest(override_model="gpt-4o"))
    kwargs = engine._completion_kwargs(route, [], None, "high")

    assert "reasoning_effort" not in kwargs


def test_deepseek_tools_omit_tool_choice():
    from plugins.agent_engine.engine import AgentEngine
    from plugins.agent_engine.model_router import ModelRouter, RouteRequest

    config = {
        "llm": {
            "providers": {
                "deepseek": {
                    "api_key": "test",
                    "base_url": "https://api.deepseek.com",
                },
            },
            "fallback_chain": ["deepseek"],
        },
        "agent": {},
    }
    router = ModelRouter(config)
    engine = AgentEngine(router, {})
    route = router.route(RouteRequest(override_model="deepseek-v4-pro"))
    kwargs = engine._completion_kwargs(
        route,
        [{"role": "user", "content": "List files"}],
        [{"name": "file_list", "parameters": {"type": "object", "properties": {}}}],
        "high",
    )

    assert kwargs["tools"][0]["function"]["name"] == "file_list"
    assert "tool_choice" not in kwargs


def test_usage_normalization_includes_cache_and_reasoning_tokens():
    from plugins.agent_engine.engine import AgentEngine

    usage = AgentEngine._normalize_usage(
        {
            "prompt_tokens": 120,
            "completion_tokens": 30,
            "total_tokens": 150,
            "prompt_tokens_details": {"cached_tokens": 80},
            "completion_tokens_details": {"reasoning_tokens": 12},
        }
    )

    assert usage == {
        "input_tokens": 120,
        "cached_input_tokens": 80,
        "cache_write_input_tokens": 0,
        "output_tokens": 30,
        "reasoning_tokens": 12,
        "total_tokens": 150,
        "requests": 1,
    }


def test_usage_normalization_supports_anthropic_cache_fields():
    from plugins.agent_engine.engine import AgentEngine

    usage = AgentEngine._normalize_usage(
        {
            "input_tokens": 90,
            "output_tokens": 10,
            "cache_read_input_tokens": 50,
            "cache_creation_input_tokens": 20,
        }
    )

    assert usage["cached_input_tokens"] == 50
    assert usage["cache_write_input_tokens"] == 20
    assert usage["total_tokens"] == 100


@pytest.mark.asyncio
async def test_streaming_usage_chunk_is_included_in_done_event(monkeypatch):
    from plugins.agent_engine.engine import AgentEngine
    from plugins.agent_engine.model_router import ModelRouter

    async def fake_stream():
        yield SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="hello", tool_calls=None),
                    finish_reason=None,
                )
            ],
            usage=None,
        )
        yield SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content=None, tool_calls=None),
                    finish_reason="stop",
                )
            ],
            usage=None,
        )
        yield SimpleNamespace(
            choices=[],
            usage={
                "prompt_tokens": 10,
                "completion_tokens": 2,
                "total_tokens": 12,
                "prompt_tokens_details": {"cached_tokens": 6},
            },
        )

    async def fake_completion(**kwargs):
        assert kwargs["stream_options"] == {"include_usage": True}
        return fake_stream()

    monkeypatch.setattr("plugins.agent_engine.engine.acompletion", fake_completion)
    config = {
        "llm": {
            "providers": {"openai": {"api_key": "test", "base_url": ""}},
            "fallback_chain": ["openai"],
        },
        "agent": {},
    }
    engine = AgentEngine(ModelRouter(config), {})

    events = [event async for event in engine.run_stream("hello", override_model="gpt-4o")]

    assert events[-1]["type"] == "done"
    assert events[-1]["usage"]["total_tokens"] == 12
    assert events[-1]["usage"]["cached_input_tokens"] == 6


@pytest.mark.asyncio
async def test_streaming_deepseek_tool_call_replays_required_fields(monkeypatch):
    from plugins.agent_engine.engine import AgentEngine
    from plugins.agent_engine.model_router import ModelRouter
    from plugins.agent_engine.tool_dispatch import ToolDispatcher

    calls = []

    async def first_stream():
        yield SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(
                        content=None,
                        reasoning_content="I should use the tool.",
                        tool_calls=[
                            SimpleNamespace(
                                index=0,
                                id="call_1",
                                type=None,
                                function=SimpleNamespace(name="echo", arguments='{"text":"hi"}'),
                            )
                        ],
                    ),
                    finish_reason="tool_calls",
                )
            ],
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        )

    async def second_stream():
        yield SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="done", reasoning_content=None, tool_calls=None),
                    finish_reason="stop",
                )
            ],
            usage={"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11},
        )

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return first_stream() if len(calls) == 1 else second_stream()

    async def echo(text):
        return text

    monkeypatch.setattr("plugins.agent_engine.engine.acompletion", fake_completion)
    config = {
        "llm": {
            "providers": {
                "deepseek": {
                    "api_key": "test",
                    "base_url": "https://api.deepseek.com",
                },
            },
            "fallback_chain": ["deepseek"],
        },
        "agent": {},
    }
    dispatcher = ToolDispatcher()
    dispatcher.register("echo", echo)
    engine = AgentEngine(ModelRouter(config), {}, dispatcher)

    events = [
        event
        async for event in engine.run_stream(
            "echo hi",
            override_model="deepseek-v4-pro",
            reasoning_effort="high",
            enabled_tools=[
                {
                    "name": "echo",
                    "parameters": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"],
                    },
                }
            ],
        )
    ]

    replayed_messages = calls[1]["messages"]
    assistant_message = replayed_messages[-2]
    assert assistant_message["content"] == ""
    assert assistant_message["reasoning_content"] == "I should use the tool."
    assert assistant_message["tool_calls"][0]["type"] == "function"
    assert replayed_messages[-1] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "hi",
    }
    assert "tool_choice" not in calls[0]
    assert events[-1]["type"] == "done"
    assert events[-1]["content"] == "done"
    assert events[-1]["usage"]["total_tokens"] == 19


def test_model_routing_reads_documented_agent_config():
    from plugins.agent_engine.model_router import ModelRouter, TaskType

    config = {
        "llm": {
            "default_model": "gpt-4o",
            "fast_model": "gpt-4o-mini",
            "providers": {
                "openai": {"api_key": "test", "base_url": ""},
                "anthropic": {"api_key": "test", "base_url": ""},
            },
            "fallback_chain": ["openai", "anthropic"],
        },
        "agent": {
            "model_routing": {
                "coding": "claude-sonnet-4",
            },
        },
    }

    router = ModelRouter(config)

    assert router.get_model_for_task(TaskType.CODING) == "claude-sonnet-4"


def test_router_excludes_failed_provider_from_fallback():
    from plugins.agent_engine.model_router import ModelRouter, RouteRequest

    config = {
        "llm": {
            "default_model": "gpt-4o",
            "fast_model": "gpt-4o-mini",
            "providers": {
                "openai": {"api_key": "openai-test", "base_url": ""},
                "anthropic": {"api_key": "anthropic-test", "base_url": ""},
            },
            "fallback_chain": ["openai", "anthropic"],
        },
        "agent": {},
    }
    router = ModelRouter(config)

    result = router.route(RouteRequest(excluded_providers={"openai"}))

    assert result.provider == "anthropic"
    assert result.routed_by == "fallback"


def test_fallback_handler_does_not_return_failed_provider():
    from plugins.agent_engine.fallback import FallbackHandler
    from plugins.agent_engine.model_router import ModelRouter, RouteRequest

    config = {
        "llm": {
            "default_model": "gpt-4o",
            "providers": {
                "openai": {"api_key": "openai-test", "base_url": ""},
                "deepseek": {"api_key": "deepseek-test", "base_url": ""},
            },
            "fallback_chain": ["openai", "deepseek"],
        },
        "agent": {},
    }
    router = ModelRouter(config)
    failed = router.route(RouteRequest(override_model="gpt-4o"))
    handler = FallbackHandler(router, ["openai", "deepseek"])

    fallback = handler.get_next(failed)

    assert fallback is not None
    assert fallback.provider == "deepseek"


@pytest.mark.asyncio
async def test_streaming_failure_moves_to_next_provider(monkeypatch):
    from plugins.agent_engine.engine import AgentEngine
    from plugins.agent_engine.model_router import ModelRouter

    calls = []

    async def successful_stream():
        yield SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="recovered", tool_calls=None),
                    finish_reason="stop",
                )
            ],
            usage={"prompt_tokens": 4, "completion_tokens": 1, "total_tokens": 5},
        )

    async def fake_completion(**kwargs):
        calls.append(kwargs["model"])
        if len(calls) == 1:
            raise RuntimeError("primary unavailable")
        return successful_stream()

    monkeypatch.setattr("plugins.agent_engine.engine.acompletion", fake_completion)
    config = {
        "llm": {
            "default_model": "gpt-4o",
            "providers": {
                "openai": {"api_key": "openai-test", "base_url": ""},
                "anthropic": {"api_key": "anthropic-test", "base_url": ""},
            },
            "fallback_chain": ["openai", "anthropic"],
        },
        "agent": {},
    }
    engine = AgentEngine(ModelRouter(config), {})

    events = [event async for event in engine.run_stream("hello")]

    assert calls[0] == "gpt-4o"
    assert calls[1].startswith("anthropic/")
    assert events[-1]["type"] == "done"
    assert events[-1]["content"] == "recovered"
    assert events[-1]["provider"] == "anthropic"


@pytest.mark.asyncio
async def test_streaming_failure_stops_when_no_distinct_fallback(monkeypatch):
    from plugins.agent_engine.engine import AgentEngine
    from plugins.agent_engine.model_router import ModelRouter

    async def fake_completion(**kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr("plugins.agent_engine.engine.acompletion", fake_completion)
    config = {
        "llm": {
            "default_model": "gpt-4o",
            "providers": {
                "openai": {"api_key": "openai-test", "base_url": ""},
            },
            "fallback_chain": ["openai"],
        },
        "agent": {},
    }
    engine = AgentEngine(ModelRouter(config), {})

    events = [event async for event in engine.run_stream("hello")]

    assert events[-1]["type"] == "error"
    assert "provider unavailable" in events[-1]["message"]
