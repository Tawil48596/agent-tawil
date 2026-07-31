"""Security tests for model-accessible file tools."""

import json

import pytest

from plugins.tool_market.builtin.file_ops import file_list, file_read, file_write


@pytest.mark.asyncio
async def test_file_read_stays_inside_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    monkeypatch.setenv("AGENT_WORKSPACE", str(workspace))

    result = json.loads(await file_read(str(outside)))

    assert "error" in result
    assert "outside" in result["error"].lower()


@pytest.mark.asyncio
async def test_file_tools_block_environment_files(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path))
    (tmp_path / ".env").write_text("OPENAI_API_KEY=secret", encoding="utf-8")

    read_result = json.loads(await file_read(".env"))
    write_result = json.loads(await file_write(".env", "replacement"))
    list_result = json.loads(await file_list("."))

    assert "error" in read_result
    assert "error" in write_result
    assert ".env" not in {item["name"] for item in list_result["items"]}


@pytest.mark.asyncio
async def test_file_read_allows_normal_workspace_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_WORKSPACE", str(tmp_path))
    (tmp_path / "notes.txt").write_text("safe content", encoding="utf-8")

    result = json.loads(await file_read("notes.txt"))

    assert result["content"] == "safe content"
