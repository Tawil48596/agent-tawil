from plugins.agent_engine.engine import AgentEngine
from plugins.agent_engine.model_router import ModelRouter
from plugins.agent_engine.tool_dispatch import ToolDispatcher
from plugins.evals.fake_llm import ScriptedLLM, ScriptedResponse


def _router() -> ModelRouter:
    return ModelRouter({
        "llm": {
            "providers": {"openai": {"api_key": "offline", "base_url": ""}},
            "fallback_chain": ["openai"],
        },
        "agent": {},
    })


async def test_scripted_llm_runs_agent_tool_loop_without_network():
    fake = ScriptedLLM([
        ScriptedResponse(tool_calls=[{
            "id": "call_1",
            "name": "echo",
            "arguments": '{"text":"hello"}',
        }]),
        ScriptedResponse(
            content="Tool returned hello",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        ),
    ])
    dispatcher = ToolDispatcher()
    dispatcher.register("echo", lambda text: text)
    engine = AgentEngine(_router(), {}, dispatcher, completion_fn=fake)

    result = await engine.run(
        "Echo hello",
        override_model="gpt-4o",
        enabled_tools=[{"name": "echo"}],
    )

    assert result.text == "Tool returned hello"
    assert result.usage["total_tokens"] == 8
    assert len(fake.requests) == 2
    assert fake.requests[1]["messages"][-1] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "hello",
    }


async def test_scripted_llm_supports_streaming_usage():
    fake = ScriptedLLM([ScriptedResponse(
        content="offline stream",
        usage={"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
    )])
    engine = AgentEngine(_router(), {}, completion_fn=fake)

    events = [
        event async for event in engine.run_stream(
            "hello", override_model="gpt-4o"
        )
    ]

    assert events[0] == {"type": "text", "content": "offline stream"}
    assert events[-1]["type"] == "done"
    assert events[-1]["usage"]["total_tokens"] == 6
