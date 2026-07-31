import base64

import pytest

from plugins.mcp_gateway.adapters.github import GitHubMCPAdapter


@pytest.mark.asyncio
async def test_github_branch_file_and_pr_workflow(monkeypatch, tmp_path):
    adapter = GitHubMCPAdapter("token", {"workspace": str(tmp_path)})
    writes = []

    async def fake_get(path, params=None):
        return {"object": {"sha": "base-sha"}}

    async def fake_write(method, path, payload):
        writes.append((method, path, payload))
        if path.endswith("/git/refs"):
            return {"object": {"sha": "base-sha"}, "url": "ref-url"}
        if "/contents/" in path:
            return {"commit": {"sha": "commit-sha"}, "content": {"html_url": "file-url"}}
        return {"number": 7, "html_url": "pr-url", "state": "open", "draft": True}

    monkeypatch.setattr(adapter, "_gh_get", fake_get)
    monkeypatch.setattr(adapter, "_gh_write", fake_write)

    branch = await adapter.call_tool("github_create_branch", {
        "owner": "o", "repo": "r", "branch": "feature"})
    updated = await adapter.call_tool("github_update_file", {
        "owner": "o", "repo": "r", "path": "README.md", "content": "hello",
        "message": "Update", "branch": "feature"})
    pull = await adapter.call_tool("github_create_pull_request", {
        "owner": "o", "repo": "r", "title": "Feature", "head": "feature", "draft": True})

    assert branch["sha"] == "base-sha"
    assert updated["commit_sha"] == "commit-sha"
    assert base64.b64decode(writes[1][2]["content"]).decode() == "hello"
    assert pull == {"number": 7, "url": "pr-url", "state": "open", "draft": True}
