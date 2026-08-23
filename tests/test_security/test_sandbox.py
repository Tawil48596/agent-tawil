import asyncio

import pytest

from plugins.security.sandbox import Sandbox, SandboxConfig


class FakeProcess:
    returncode = 0

    async def communicate(self):
        return b"ok", b""


@pytest.mark.asyncio
async def test_docker_mode_applies_read_only_root_and_network_policy(tmp_path, monkeypatch):
    captured = []

    async def fake_subprocess(*args, **kwargs):
        captured.extend(args)
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess)
    sandbox = Sandbox(SandboxConfig(mode="docker", workspace=str(tmp_path), read_only_root=True))

    result = await sandbox.execute("echo ok")

    assert result.stdout == "ok"
    assert "--read-only" in captured
    assert captured[captured.index("--network") + 1] == "none"
    assert "/tmp:exec" in captured
