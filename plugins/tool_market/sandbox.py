"""工具执行沙箱 — Docker / subprocess 隔离"""

import asyncio
import os
from dataclasses import dataclass, field


@dataclass
class SandboxConfig:
    mode: str = "subprocess"
    docker_image: str = "ai-agent-sandbox:latest"
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    timeout: int = 30
    network_enabled: bool = False
    read_only_root: bool = True


class ToolSandbox:
    """工具执行沙箱"""

    def __init__(self, config: SandboxConfig = None):
        self._config = config or SandboxConfig()

    async def execute(self, command: str, workdir: str = "", env: dict = None) -> dict:
        if self._config.mode == "docker":
            return await self._docker_exec(command, workdir, env)
        return await self._subprocess_exec(command, workdir, env)

    async def _subprocess_exec(self, command: str, workdir: str, env: dict) -> dict:
        try:
            import asyncio
            clean_env = {k: os.environ[k] for k in ["PATH", "HOME", "USER", "LANG"] if k in os.environ}
            if env: clean_env.update(env)
            proc = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=workdir or ".", env=clean_env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self._config.timeout)
            return {"stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace"), "exit_code": proc.returncode or 0}
        except asyncio.TimeoutError:
            return {"error": "timeout", "exit_code": -1}

    async def _docker_exec(self, command: str, workdir: str, env: dict) -> dict:
        args = ["docker", "run", "--rm", f"--memory={self._config.memory_limit}", f"--cpus={self._config.cpu_limit}"]
        if not self._config.network_enabled: args.append("--network=none")
        if self._config.read_only_root: args.extend(["--read-only", "--tmpfs", "/tmp:exec"])
        if workdir: args.extend(["-v", f"{workdir}:{workdir}", "-w", workdir])
        args.append(self._config.docker_image)
        args.extend(["sh", "-c", command])
        try:
            proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self._config.timeout)
            return {"stdout": stdout.decode(errors="replace"), "stderr": stderr.decode(errors="replace"), "exit_code": proc.returncode or 0}
        except asyncio.TimeoutError:
            return {"error": "timeout", "exit_code": -1}
