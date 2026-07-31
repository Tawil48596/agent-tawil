"""Test Agent Engine"""

import pytest


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
