"""Tests for retrying an interrupted chat request."""

from plugins.web_ui.api.chat import (
    _add_session_usage,
    _append_user_message,
    _messages,
    _session_usage,
)


def test_retry_does_not_duplicate_pending_user_message():
    session_id = "retry-test"
    _messages[session_id] = []

    _append_user_message(session_id, "continue this task", retry=False)
    _append_user_message(session_id, "continue this task", retry=True)

    assert _messages[session_id] == [
        {"role": "user", "content": "continue this task"},
    ]


def test_normal_repeat_remains_a_new_user_message():
    session_id = "repeat-test"
    _messages[session_id] = []

    _append_user_message(session_id, "again", retry=False)
    _append_user_message(session_id, "again", retry=False)

    assert len(_messages[session_id]) == 2


def test_session_usage_accumulates_and_calculates_cache_hit_rate():
    session_id = "usage-test"
    _session_usage.pop(session_id, None)

    _add_session_usage(
        session_id,
        {
            "input_tokens": 100,
            "cached_input_tokens": 40,
            "output_tokens": 20,
            "reasoning_tokens": 5,
            "total_tokens": 120,
            "requests": 1,
        },
    )
    result = _add_session_usage(
        session_id,
        {
            "input_tokens": 50,
            "cached_input_tokens": 20,
            "cache_write_input_tokens": 10,
            "output_tokens": 10,
            "total_tokens": 60,
            "requests": 1,
        },
    )

    assert result["requests"] == 2
    assert result["total_tokens"] == 180
    assert result["cached_input_tokens"] == 60
    assert result["cache_write_input_tokens"] == 10
    assert result["cache_hit_rate"] == 0.4
