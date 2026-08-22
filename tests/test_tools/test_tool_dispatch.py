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


@pytest.mark.asyncio
async def test_approval_required_tool_fails_closed_without_handler():
    dispatcher = ToolDispatcher()
    called = False

    async def handler():
        nonlocal called
        called = True
        return "ok"

    dispatcher.register("dangerous", handler, requires_approval=True)
    result = await dispatcher.execute_parallel([_call("dangerous", "{}")])

    assert result[0]["code"] == "approval_required"
    assert called is False


@pytest.mark.asyncio
async def test_external_approval_allows_dangerous_tool():
    decisions = []

    async def approve(name, arguments, context):
        decisions.append((name, arguments))
        assert context == {"id": "session-1"}
        return True

    dispatcher = ToolDispatcher(approval_handler=approve)
    dispatcher.register("dangerous", lambda value: value, requires_approval=True)

    result = await dispatcher.execute_parallel(
        [_call("dangerous", json.dumps({"value": "approved"}))],
        context={"id": "session-1"},
    )

    assert result[0]["error"] is False
    assert result[0]["output"] == "approved"
    assert decisions == [("dangerous", {"value": "approved"})]


@pytest.mark.asyncio
async def test_external_denial_blocks_dangerous_tool():
    dispatcher = ToolDispatcher(
        approval_handler=lambda _name, _arguments, _context: False
    )
    dispatcher.register("dangerous", lambda: "must not run", requires_approval=True)

    result = await dispatcher.execute_parallel([_call("dangerous", "{}")])

    assert result[0]["code"] == "approval_denied"


@pytest.mark.asyncio
async def test_model_arguments_cannot_self_approve_tool_call():
    dispatcher = ToolDispatcher()
    dispatcher.register("dangerous", lambda approved=False: approved, requires_approval=True)

    result = await dispatcher.execute_parallel([
        _call("dangerous", json.dumps({"approved": True}))
    ])

    assert result[0]["code"] == "approval_required"
