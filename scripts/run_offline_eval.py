"""Run a deterministic Agent tool-loop evaluation without API keys or network."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from plugins.agent_engine.engine import AgentEngine  # noqa: E402
from plugins.agent_engine.model_router import ModelRouter  # noqa: E402
from plugins.agent_engine.tool_dispatch import ToolDispatcher  # noqa: E402
from plugins.evals.fake_llm import ScriptedLLM, ScriptedResponse  # noqa: E402
from plugins.evals.runner import EvalRunner  # noqa: E402


async def run(history_path: Path) -> dict:
    fake = ScriptedLLM([
        ScriptedResponse(tool_calls=[{
            "id": "offline_call_1",
            "name": "echo",
            "arguments": '{"text":"hello"}',
        }]),
        ScriptedResponse(
            content="Tool returned hello",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        ),
    ])
    router = ModelRouter({
        "llm": {
            "providers": {"openai": {"api_key": "offline", "base_url": ""}},
            "fallback_chain": ["openai"],
        },
        "agent": {},
    })
    dispatcher = ToolDispatcher()
    dispatcher.register("echo", lambda text: text)
    engine = AgentEngine(router, {}, dispatcher, completion_fn=fake)

    async def agent_fn(text: str) -> dict:
        response = await engine.run(
            text,
            override_model="gpt-4o",
            enabled_tools=[{"name": "echo"}],
        )
        return {
            "text": response.text,
            "tools": [call["function"]["name"] for call in response.tool_calls],
            "usage": response.usage,
        }

    runner = EvalRunner(
        str(ROOT / "plugins" / "evals" / "test_suites"),
        history_path=str(history_path),
    )
    return await runner.run("offline_smoke", agent_fn)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--history",
        type=Path,
        default=ROOT / "data" / "evals" / "offline_history.json",
    )
    report = asyncio.run(run(parser.parse_args().history))
    summary = {
        "run_id": report.get("run_id"),
        "suite": report.get("suite"),
        "pass_rate": report.get("pass_rate"),
        "metrics": report.get("metrics"),
        "regression": report.get("regression"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if report.get("pass_rate") == 1.0 and report["regression"]["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
