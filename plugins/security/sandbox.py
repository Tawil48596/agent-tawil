"""容器化沙箱 — 双模式 (subprocess + Docker) + 资源限制 + 超时保护"""

import asyncio
import os
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
    was_blocked: bool = False


@dataclass
class SandboxConfig:
    mode: str = "subprocess"  # subprocess | docker
    docker_image: str = "ai-agent-sandbox:latest"
    workspace: str = field(default_factory=lambda: os.path.expanduser("~/agent_workspace"))
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    timeout: int = 30
    network_enabled: bool = False
    read_only_root: bool = True
    allowed_env_vars: list[str] = field(default_factory=lambda: ["PATH", "HOME", "USER", "LANG"])


class Sandbox:
    """代码/命令执行沙箱"""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self._config = config or SandboxConfig()
        Path(self._config.workspace).mkdir(parents=True, exist_ok=True)

    @property
    def mode(self) -> str:
        return self._config.mode

    async def execute(
        self,
        command: str,
        workdir: str = "",
        env: Optional[dict[str, str]] = None,
        stdin: str = "",
    ) -> SandboxResult:
        """执行命令，自动选择 subprocess 或 Docker 模式"""
        if self._config.mode == "docker":
            return await self._execute_docker(command, workdir, env, stdin)
        else:
            return await self._execute_subprocess(command, workdir, env, stdin)

    # ── Subprocess 模式 ──

    async def _execute_subprocess(
        self, command: str, workdir: str, env: dict = None, stdin: str = ""
    ) -> SandboxResult:
        workdir = workdir or self._config.workspace
        Path(workdir).mkdir(parents=True, exist_ok=True)

        # 受限环境变量
        clean_env = {}
        for key in self._config.allowed_env_vars:
            if key in os.environ:
                clean_env[key] = os.environ[key]
        if env:
            clean_env.update(env)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if stdin else None,
                cwd=workdir,
                env=clean_env,
                # 进程组隔离
                preexec_fn=os.setsid if os.name != "nt" else None,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin.encode() if stdin else None),
                timeout=self._config.timeout,
            )

            return SandboxResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else "",
                stderr=stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else "",
                exit_code=proc.returncode or 0,
            )

        except asyncio.TimeoutError:
            if proc:
                try:
                    proc.kill()
                except Exception:
                    pass
            return SandboxResult(
                stdout="", stderr="命令执行超时", exit_code=-1, timed_out=True,
            )

    # ── Docker 模式 ──

    async def _execute_docker(
        self, command: str, workdir: str, env: dict = None, stdin: str = ""
    ) -> SandboxResult:
        workdir = workdir or self._config.workspace

        docker_args = [
            "docker", "run", "--rm",
            "--memory", self._config.memory_limit,
            "--cpus", str(self._config.cpu_limit),
            "--network", "none" if not self._config.network_enabled else "bridge",
            "--read-only" if self._config.read_only else "",
            "-v", f"{workdir}:{workdir}",
            "-w", workdir,
        ]
        if self._config.read_only:
            docker_args.extend(["--tmpfs", "/tmp:exec"])

        docker_args = [a for a in docker_args if a]  # 过滤空字符串
        docker_args.append(self._config.docker_image)
        docker_args.extend(["sh", "-c", command])

        try:
            proc = await asyncio.create_subprocess_exec(
                *docker_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._config.timeout,
            )
            return SandboxResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else "",
                stderr=stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else "",
                exit_code=proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            return SandboxResult(stdout="", stderr="命令执行超时", exit_code=-1, timed_out=True)

    # ── 简单接口 ──

    async def run_python(self, code: str) -> SandboxResult:
        """在沙箱中运行 Python 代码"""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=self._config.workspace) as f:
            f.write(code)
            tmp_path = f.name
        try:
            return await self.execute(f"python {shlex.quote(tmp_path)}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
