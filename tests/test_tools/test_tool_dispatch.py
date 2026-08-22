import json

import pytest

from plugins.agent_engine.tool_dispatch import ToolDispatcher
from plugins.checkpoint.execution_ledger import ToolExecutionLedger


def _call(name: str, arguments: str, call_id: str = "") -> dict:
    call = {"function": {"name": name, "arguments": arguments}}
    if call_id:
        call["id"] = call_id
    return call


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


@pytest.mark.asyncio
async def test_successful_tool_call_is_replayed_after_dispatcher_restart(tmp_path):
    calls = 0

    async def side_effect():
        nonlocal calls
        calls += 1
        return "created"

    ledger = ToolExecutionLedger(tmp_path)
    first = ToolDispatcher()
    first.set_execution_ledger(ledger)
    first.register("create", side_effect)
    result = await first.execute_parallel(
        [_call("create", "{}", "call-1")], context={"id": "session-1"}
    )

    restarted = ToolDispatcher()
    restarted.set_execution_ledger(ToolExecutionLedger(tmp_path))
    restarted.register("create", side_effect)
    replay = await restarted.execute_parallel(
        [_call("create", "{}", "call-1")], context={"id": "session-1"}
    )

    assert result[0]["error"] is False
    assert replay[0]["replayed"] is True
    assert calls == 1


@pytest.mark.asyncio
async def test_failed_tool_call_is_not_cached(tmp_path):
    calls = 0

    async def retryable():
        nonlocal calls
        calls += 1
        return {"error": "try again"}

    dispatcher = ToolDispatcher()
    dispatcher.set_execution_ledger(ToolExecutionLedger(tmp_path))
    dispatcher.register("retryable", retryable)
    call = _call("retryable", "{}", "call-1")

    await dispatcher.execute_parallel([call], context={"id": "session-1"})
    await dispatcher.execute_parallel([call], context={"id": "session-1"})

    assert calls == 2


@pytest.mark.asyncio
async def test_changed_arguments_do_not_replay_same_call_id(tmp_path):
    calls = 0

    async def echo(value):
        nonlocal calls
        calls += 1
        return value

    dispatcher = ToolDispatcher()
    dispatcher.set_execution_ledger(ToolExecutionLedger(tmp_path))
    dispatcher.register("echo", echo)

    await dispatcher.execute_parallel(
        [_call("echo", '{"value":"first"}', "call-1")], context={"id": "session-1"}
    )
    changed = await dispatcher.execute_parallel(
        [_call("echo", '{"value":"second"}', "call-1")], context={"id": "session-1"}
    )

    assert changed[0]["output"] == "second"
    assert calls == 2
