"""Tests for retrying an interrupted chat request."""

from plugins.web_ui.api.chat import _append_user_message, _messages


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
