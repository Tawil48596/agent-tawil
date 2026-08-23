import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from plugins.agent_engine.tool_dispatch import ToolDispatcher
from plugins.checkpoint.execution_ledger import ToolExecutionLedger
from plugins.web_ui.api.tools import ExecutionResolveRequest, resolve_uncertain_execution


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
    dispatcher = ToolDispatcher(approval_handler=lambda _name, _arguments, _context: False)
    dispatcher.register("dangerous", lambda: "must not run", requires_approval=True)

    result = await dispatcher.execute_parallel([_call("dangerous", "{}")])

    assert result[0]["code"] == "approval_denied"


@pytest.mark.asyncio
async def test_model_arguments_cannot_self_approve_tool_call():
    dispatcher = ToolDispatcher()
    dispatcher.register("dangerous", lambda approved=False: approved, requires_approval=True)

    result = await dispatcher.execute_parallel([_call("dangerous", json.dumps({"approved": True}))])

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

    assert changed[0]["code"] == "tool_call_conflict"
    assert calls == 1


def test_active_and_expired_leases_fail_closed_until_resolved(tmp_path):
    ledger = ToolExecutionLedger(tmp_path, lease_seconds=60)
    first = ledger.acquire("session-1", "call-1", "write", {"value": 1})

    assert first["action"] == "execute"
    assert ledger.acquire("session-1", "call-1", "write", {"value": 1})["action"] == "busy"

    expired = ToolExecutionLedger(tmp_path, lease_seconds=0)
    path = expired._entry_path("session-1", "call-1")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["lease_expires_at"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert expired.acquire("session-1", "call-1", "write", {"value": 1})["action"] == "uncertain"
    assert expired.resolve_uncertain("session-1", "call-1") is True
    assert expired.acquire("session-1", "call-1", "write", {"value": 1})["action"] == "execute"


@pytest.mark.asyncio
async def test_handler_exception_becomes_uncertain(tmp_path):
    async def may_have_written():
        raise RuntimeError("connection lost after write")

    dispatcher = ToolDispatcher()
    dispatcher.set_execution_ledger(ToolExecutionLedger(tmp_path))
    dispatcher.register("write", may_have_written)
    call = _call("write", "{}", "call-1")

    first = await dispatcher.execute_parallel([call], context={"id": "session-1"})
    retry = await dispatcher.execute_parallel([call], context={"id": "session-1"})

    assert first[0]["error"] is True
    assert retry[0]["code"] == "tool_execution_uncertain"


@pytest.mark.asyncio
async def test_uncertain_resolution_requires_explicit_confirmation(tmp_path):
    ledger = ToolExecutionLedger(tmp_path, lease_seconds=0)
    ledger.acquire("session-1", "call-1", "write", {})
    ledger.acquire("session-1", "call-1", "write", {})
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(execution_ledger=ledger)))

    with pytest.raises(HTTPException) as denied:
        await resolve_uncertain_execution(
            ExecutionResolveRequest(session_id="session-1", call_id="call-1"), request
        )

    assert denied.value.status_code == 400
    resolved = await resolve_uncertain_execution(
        ExecutionResolveRequest(session_id="session-1", call_id="call-1", confirm_reconciled=True),
        request,
    )
    assert resolved["ok"] is True
