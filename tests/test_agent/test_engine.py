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
