import pytest


def test_session_store_persists_messages_usage_and_deletion(tmp_path):
    from plugins.conversation.session_store import SessionStore

    database = tmp_path / "agent.db"
    store = SessionStore(str(database))
    store.connect()

    session_id = store.create_session(title="新对话")
    store.add_message(session_id, "user", "请检查项目")
    store.update_session(session_id, title="请检查项目")
    store.add_message(
        session_id,
        "assistant",
        "检查完成",
        model="deepseek-v4-pro",
        provider="deepseek",
        token_count=15,
        usage={
            "input_tokens": 10,
            "cached_input_tokens": 4,
            "output_tokens": 5,
            "total_tokens": 15,
            "requests": 1,
        },
    )
    store.close()

    reopened = SessionStore(str(database))
    reopened.connect()
    sessions = reopened.list_sessions()
    messages = reopened.get_messages(session_id)
    usage = reopened.get_session_usage(session_id)

    assert sessions[0]["title"] == "请检查项目"
    assert sessions[0]["message_count"] == 2
    assert [message["content"] for message in messages] == ["请检查项目", "检查完成"]
    assert messages[1]["model"] == "deepseek-v4-pro"
    assert usage["total_tokens"] == 15
    assert usage["cache_hit_rate"] == 0.4

    assert reopened.delete_session(session_id) is True
    assert reopened.get_session(session_id) is None
    assert reopened.get_messages(session_id) == []
    reopened.close()


@pytest.mark.asyncio
async def test_builtin_long_term_memory_survives_restart(tmp_path):
    from plugins.memory.long_term import LongTermMemory, MemoryEntry

    storage_path = tmp_path / "memory.json"
    config = {
        "memory": {
            "long_term_backend": "builtin",
            "storage_path": str(storage_path),
            "importance_threshold": 0.3,
        },
    }
    memory = LongTermMemory(config)
    entry_id = await memory.save(
        MemoryEntry(
            id="",
            content="用户偏好简洁界面",
            type="preference",
            importance=0.8,
        )
    )

    reopened = LongTermMemory(config)
    restored = await reopened.get(entry_id)
    assert restored is not None
    assert restored.content == "用户偏好简洁界面"

    await reopened.delete(entry_id)
    assert LongTermMemory(config).count == 0


@pytest.mark.asyncio
async def test_memory_metadata_filters_updates_and_scoped_clear(tmp_path):
    from plugins.memory.long_term import LongTermMemory, MemoryEntry

    config = {
        "memory": {
            "long_term_backend": "builtin",
            "storage_path": str(tmp_path / "memory.json"),
            "importance_threshold": 0.1,
        },
    }
    memory = LongTermMemory(config)
    project_a_id = await memory.save(MemoryEntry(
        id="",
        content="Use PostgreSQL for production",
        source="conversation",
        source_session="session-a",
        user_id="user-a",
        project_id="project-a",
        tags=["database"],
        confidence=0.9,
    ))
    duplicate_id = await memory.save(MemoryEntry(
        id="",
        content="  use PostgreSQL for production  ",
        user_id="user-a",
        project_id="project-a",
        importance=0.8,
    ))
    await memory.save(MemoryEntry(
        id="",
        content="Use SQLite for prototypes",
        source="manual",
        user_id="user-a",
        project_id="project-b",
    ))

    isolated = await memory.search(
        "production",
        user_id="user-a",
        project_id="project-a",
    )
    assert duplicate_id == project_a_id
    assert [entry.id for entry in isolated] == [project_a_id]
    assert isolated[0].source_session == "session-a"
    assert isolated[0].tags == ["database"]

    updated = await memory.update(
        project_a_id,
        content="Use PostgreSQL 17 for production",
        confidence=0.95,
    )
    assert updated is not None
    assert updated.confidence == 0.95

    await memory.clear(user_id="user-a", project_id="project-a")
    restarted = LongTermMemory(config)
    assert restarted.list_entries(project_id="project-a") == []
    assert len(restarted.list_entries(project_id="project-b")) == 1
