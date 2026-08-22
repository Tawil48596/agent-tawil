from plugins.evals.trace_viewer import TraceCollector
from plugins.observability.metrics import MetricsCollector


def test_tool_and_llm_metrics_contain_no_payload_data():
    metrics = MetricsCollector()

    metrics.record_tool_event(
        "tool.completed", duration_ms=12.5, arguments={"password": "secret"}
    )
    metrics.record_tool_event("untrusted.dynamic.event", value=99)
    metrics.record_llm_usage({
        "requests": 1,
        "input_tokens": 20,
        "cached_input_tokens": 8,
        "output_tokens": 5,
        "total_tokens": 25,
    })

    result = metrics.get_all()
    assert result["counters"]["tool_completed_total"] == 1
    assert result["counters"]["llm_total_tokens_total"] == 25
    assert result["counters"]["llm_cached_input_tokens_total"] == 8
    assert "untrusted_dynamic_event_total" not in result["counters"]
    assert "secret" not in str(result)


def test_trace_reuses_http_trace_id_and_summarizes_tool_result():
    collector = TraceCollector()
    root = collector.start_trace("chat", trace_id="request-trace")
    tool = collector.add_span(root, "tool_call", "echo")
    collector.end_span(tool, output={"error": False, "replayed": True})
    collector.end_span(root, tokens_in=10, tokens_out=4)

    assert collector.get_trace("request-trace") is root
    assert collector.list_traces()[0]["total_tokens"] == 14
    assert root.children[0].output == {"error": False, "replayed": True}


def test_trace_summary_survives_restart_without_payloads(tmp_path):
    path = tmp_path / "traces" / "history.json"
    collector = TraceCollector(storage_path=str(path))
    root = collector.start_trace("chat", trace_id="trace-1")
    tool = collector.add_span(
        root, "tool_call", "write", input_data={"password": "secret"}
    )
    collector.end_span(tool, output={"content": "private"}, error="tool_error")
    collector.end_span(root, tokens_in=4, tokens_out=2)

    restarted = TraceCollector(storage_path=str(path))
    restored = restarted.get_trace("trace-1")

    assert restored is not None
    assert restored.children[0].name == "write"
    assert restarted.list_traces(error_only=True)[0]["trace_id"] == "trace-1"
    persisted = path.read_text(encoding="utf-8")
    assert "secret" not in persisted
    assert "private" not in persisted
