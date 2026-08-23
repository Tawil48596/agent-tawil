import json

import pytest

from plugins.agent_engine.tool_dispatch import ToolDispatcher
from plugins.observability.audit import AuditLog, redact_sensitive


def test_redact_sensitive_recurses_without_mutating_input():
    source = {
        "password": "visible",
        "nested": {"api_key": "sk-private", "safe": "kept"},
        "items": [{"access_token": "token-value"}],
    }

    result = redact_sensitive(source)

    assert result == {
        "password": "[REDACTED]",
        "nested": {"api_key": "[REDACTED]", "safe": "kept"},
        "items": [{"access_token": "[REDACTED]"}],
    }
    assert source["password"] == "visible"


def test_audit_log_writes_redacted_jsonl(tmp_path):
    path = tmp_path / "audit" / "events.jsonl"
    audit = AuditLog({"path": str(path)})

    assert audit.record(
        "tool.started",
        trace_id="trace-1",
        arguments={"query": "public", "authorization": "Bearer secret"},
    )

    event = json.loads(path.read_text(encoding="utf-8"))
    assert event["event_type"] == "tool.started"
    assert event["trace_id"] == "trace-1"
    assert event["arguments"] == {
        "query": "public",
        "authorization": "[REDACTED]",
    }
    assert event["event_id"]
    assert event["timestamp"].endswith("+00:00")


def test_disabled_audit_log_does_not_create_file(tmp_path):
    path = tmp_path / "events.jsonl"

    assert AuditLog({"enabled": False, "path": str(path)}).record("ignored") is False
    assert not path.exists()


@pytest.mark.asyncio
async def test_dispatcher_audit_events_preserve_trace_and_redact_arguments(tmp_path):
    path = tmp_path / "events.jsonl"
    audit = AuditLog({"path": str(path)})
    dispatcher = ToolDispatcher()
    dispatcher.set_audit_handler(audit.record)
    dispatcher.register("credential_check", lambda password: "ok")

    result = await dispatcher.execute_parallel(
        [{
            "function": {
                "name": "credential_check",
                "arguments": '{"password":"secret"}',
            }
        }],
        context={"id": "session-1", "trace_id": "trace-1"},
    )

    events = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]
    started = next(event for event in events if event["event_type"] == "tool.started")
    assert result[0]["output"] == "ok"
    assert started["arguments"]["password"] == "[REDACTED]"
    assert started["context"]["trace_id"] == "trace-1"
