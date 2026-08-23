import json

import pytest

from plugins.agent_engine.engine import AgentEngine
from plugins.agent_engine.model_router import ModelRouter
from plugins.agent_engine.tool_dispatch import ToolDispatcher
from plugins.evals.fake_llm import ScriptedLLM, ScriptedResponse
from plugins.evals.runner import EvalRunner
from shared.versioned_store import UnsupportedSchemaVersion, load_collection


def _router() -> ModelRouter:
    return ModelRouter(
        {
            "llm": {
                "providers": {"openai": {"api_key": "offline", "base_url": ""}},
                "fallback_chain": ["openai"],
            },
            "agent": {},
        }
    )


async def test_scripted_llm_runs_agent_tool_loop_without_network():
    fake = ScriptedLLM(
        [
            ScriptedResponse(
                tool_calls=[
                    {
                        "id": "call_1",
                        "name": "echo",
                        "arguments": '{"text":"hello"}',
                    }
                ]
            ),
            ScriptedResponse(
                content="Tool returned hello",
                usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            ),
        ]
    )
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
    assert result.tool_calls[0]["function"]["name"] == "echo"
    assert len(fake.requests) == 2
    assert fake.requests[1]["messages"][-1] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "hello",
    }


async def test_scripted_llm_supports_streaming_usage():
    fake = ScriptedLLM(
        [
            ScriptedResponse(
                content="offline stream",
                usage={"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
            )
        ]
    )
    engine = AgentEngine(_router(), {}, completion_fn=fake)

    events = [event async for event in engine.run_stream("hello", override_model="gpt-4o")]

    assert events[0] == {"type": "text", "content": "offline stream"}
    assert events[-1]["type"] == "done"
    assert events[-1]["usage"]["total_tokens"] == 6


async def test_eval_runner_scores_tools_tokens_and_text(tmp_path):
    (tmp_path / "offline.yaml").write_text(
        """name: offline
cases:
  - id: uses_echo
    input: echo hello
    expected:
      keywords: [hello]
      tools: [echo]
      tool_arguments:
        echo: {value: hello}
      max_total_tokens: 20
""",
        encoding="utf-8",
    )
    history_path = tmp_path / "history.json"
    runner = EvalRunner(str(tmp_path), history_path=str(history_path))

    async def agent_fn(_text: str) -> dict:
        return {
            "text": "hello",
            "tools": ["echo"],
            "tool_arguments": {"echo": {"value": "hello"}},
            "usage": {"total_tokens": 12},
        }

    report = await runner.run("offline", agent_fn)

    assert report["pass_rate"] == 1.0
    assert report["metrics"]["tool_accuracy"] == 1.0
    assert report["metrics"]["argument_accuracy"] == 1.0
    assert report["metrics"]["budget_failures"] == 0
    assert report["metrics"]["avg_tokens"] == 12
    assert report["regression"]["baseline_found"] is False

    async def regressed_agent(_text: str) -> dict:
        return {"text": "miss", "tools": [], "usage": {"total_tokens": 2}}

    restarted = EvalRunner(str(tmp_path), history_path=str(history_path))
    regressed = await restarted.run("offline", regressed_agent)

    assert len(restarted.get_history("offline")) == 2
    assert regressed["regression"]["baseline_run_id"] == report["run_id"]
    assert regressed["regression"]["pass_rate_delta"] == -1.0
    assert regressed["regression"]["gate_passed"] is False
    assert json.loads(history_path.read_text(encoding="utf-8"))["schema_version"] == 1


async def test_eval_budget_failure_is_reported_without_output_payload(tmp_path):
    (tmp_path / "budget.yaml").write_text(
        """name: budget
cases:
  - id: over_budget
    input: test
    expected: {keywords: [ok], max_total_tokens: 5}
""",
        encoding="utf-8",
    )
    runner = EvalRunner(str(tmp_path))

    async def agent_fn(_text):
        return {"text": "ok", "usage": {"total_tokens": 6}}

    report = await runner.run("budget", agent_fn)

    assert report["pass_rate"] == 0.0
    assert report["metrics"]["budget_failures"] == 1
    assert "text" not in report["results"][0]


def test_eval_history_rejects_unknown_schema_version(tmp_path):
    path = tmp_path / "history.json"
    path.write_text('{"schema_version":99,"items":[]}', encoding="utf-8")

    with pytest.raises(UnsupportedSchemaVersion):
        EvalRunner(str(tmp_path), history_path=str(path))


def test_versioned_store_reads_legacy_list(tmp_path):
    path = tmp_path / "legacy.json"
    path.write_text('[{"id":"old"},null]', encoding="utf-8")

    assert load_collection(path) == [{"id": "old"}]
