import json

import pytest

from plugins.agent_engine.tool_dispatch import ToolDispatcher


def _call(name: str, arguments: str) -> dict:
    return {"function": {"name": name, "arguments": arguments}}


@pytest.mark.asyncio
async def test_structured_tool_error_is_reported_as_failure():
    dispatcher = ToolDispatcher()

    async def failing_tool():
        return json.dumps({"error": "upstream denied access"})

    dispatcher.register("failing", failing_tool)
    result = await dispatcher.execute_parallel([_call("failing", "{}")])

    assert result[0]["error"] is True
    assert "upstream denied access" in result[0]["output"]


@pytest.mark.asyncio
async def test_dict_tool_error_is_serialized_and_reported_as_failure():
    dispatcher = ToolDispatcher()

    async def failing_tool():
        return {"error": "permission denied"}

    dispatcher.register("failing", failing_tool)
    result = await dispatcher.execute_parallel([_call("failing", "{}")])

    assert result[0]["error"] is True
    assert json.loads(result[0]["output"]) == {"error": "permission denied"}


@pytest.mark.asyncio
async def test_invalid_json_arguments_do_not_call_handler():
    dispatcher = ToolDispatcher()
    called = False

    async def handler():
        nonlocal called
        called = True
        return "ok"

    dispatcher.register("example", handler)
    result = await dispatcher.execute_parallel([_call("example", "{broken")])

    assert result[0]["error"] is True
    assert "有效 JSON" in result[0]["output"]
    assert called is False


@pytest.mark.asyncio
async def test_non_object_arguments_are_rejected():
    dispatcher = ToolDispatcher()
    dispatcher.register("example", lambda: "ok")

    result = await dispatcher.execute_parallel([_call("example", "[]")])

    assert result[0]["error"] is True
    assert "JSON 对象" in result[0]["output"]
