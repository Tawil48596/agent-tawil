"""pytest 共享 fixtures"""

import asyncio
import contextlib
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop():
    """创建 session 级 event loop"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_dir():
    """临时测试目录"""
    with tempfile.TemporaryDirectory(prefix="ai-agent-test-") as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_session():
    """提供示例会话数据"""
    from shared.models import Session

    return Session(title="Test Session", source="test")


@pytest.fixture
def sample_message(sample_session):
    """提供示例消息数据"""
    from shared.models import Message

    return Message(session_id=sample_session.id, role="user", content="Hello")


@pytest.fixture
def sample_tool_definition():
    """提供示例工具定义"""
    from shared.models import ToolDefinition

    return ToolDefinition(
        name="echo",
        description="Echo back the input",
        parameters={"text": {"type": "string", "description": "Text to echo"}},
        toolset="test",
    )


@pytest.fixture
def sample_memory_entry():
    """提供示例记忆条目"""
    from shared.models import MemoryEntry

    return MemoryEntry(
        content="User prefers Python",
        type="preference",
        importance=0.8,
    )


# ── Async fixtures ──


@pytest_asyncio.fixture
async def temp_db():
    """临时 SQLite 数据库"""
    db_path = f"sqlite+aiosqlite:///test_{os.urandom(4).hex()}.db"
    yield db_path
    # cleanup
    import glob

    for f in glob.glob("test_*.db"):
        with contextlib.suppress(OSError):
            os.remove(f)
