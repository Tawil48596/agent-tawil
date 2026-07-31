"""Test Agent Engine"""

import pytest
from types import SimpleNamespace


def test_model_router_initialization():
    from plugins.agent_engine.model_router import ModelRouter
    config = {
        "llm": {"default_model": "gpt-4o", "fast_model": "gpt-4o-mini",
                "providers": {"openai": {"api_key": "test", "base_url": ""}},
                "model_routing": {}, "fallback_chain": ["openai"]},
        "agent": {"max_turns": 10},
    }
    router = ModelRouter(config)
    assert router._default_model == "gpt-4o"
    models = router.list_available_models()
    assert len(models) >= 1


def test_route_override():
    from plugins.agent_engine.model_router import ModelRouter, RouteRequest, TaskType
    config = {
        "llm": {"default_model": "gpt-4o", "fast_model": "gpt-4o-mini",
                "providers": {"openai": {"api_key": "test", "base_url": ""}},
                "model_routing": {}, "fallback_chain": ["openai"]},
        "agent": {"max_turns": 10},
    }
    router = ModelRouter(config)
    result = router.route(RouteRequest(override_model="gpt-4o"))
    assert result.routed_by == "override"
    assert result.model == "gpt-4o"


def test_task_routing():
    from plugins.agent_engine.model_router import ModelRouter, RouteRequest, TaskType
    config = {
        "llm": {"default_model": "gpt-4o", "fast_model": "gpt-4o-mini",
                "providers": {"openai": {"api_key": "test", "base_url": ""}},
                "model_routing": {"summarization": "gpt-4o-mini"},
                "fallback_chain": ["openai"]},
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
        [{
            "name": "get_current_time",
            "description": "Get the current time",
            "parameters": {"type": "object", "properties": {}},
        }],
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


def test_usage_normalization_includes_cache_and_reasoning_tokens():
    from plugins.agent_engine.engine import AgentEngine

    usage = AgentEngine._normalize_usage({
        "prompt_tokens": 120,
        "completion_tokens": 30,
        "total_tokens": 150,
        "prompt_tokens_details": {"cached_tokens": 80},
        "completion_tokens_details": {"reasoning_tokens": 12},
    })

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

    usage = AgentEngine._normalize_usage({
        "input_tokens": 90,
        "output_tokens": 10,
        "cache_read_input_tokens": 50,
        "cache_creation_input_tokens": 20,
    })

    assert usage["cached_input_tokens"] == 50
    assert usage["cache_write_input_tokens"] == 20
    assert usage["total_tokens"] == 100


@pytest.mark.asyncio
async def test_streaming_usage_chunk_is_included_in_done_event(monkeypatch):
    from plugins.agent_engine.engine import AgentEngine
    from plugins.agent_engine.model_router import ModelRouter

    async def fake_stream():
        yield SimpleNamespace(
            choices=[SimpleNamespace(
                delta=SimpleNamespace(content="hello", tool_calls=None),
                finish_reason=None,
            )],
            usage=None,
        )
        yield SimpleNamespace(
            choices=[SimpleNamespace(
                delta=SimpleNamespace(content=None, tool_calls=None),
                finish_reason="stop",
            )],
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

    events = [
        event async for event in engine.run_stream(
            "hello", override_model="gpt-4o"
        )
    ]

    assert events[-1]["type"] == "done"
    assert events[-1]["usage"]["total_tokens"] == 12
    assert events[-1]["usage"]["cached_input_tokens"] == 6
