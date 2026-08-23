"""内置工具: terminal — Shell 命令执行"""

import asyncio
import json
import os


async def terminal_exec(command: str, workdir: str = "", timeout: int = 30) -> str:
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workdir or os.getcwd(),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return json.dumps(
            {
                "stdout": stdout.decode(errors="replace")[:5000],
                "stderr": stderr.decode(errors="replace")[:1000],
                "exit_code": proc.returncode or 0,
            }
        )
    except TimeoutError:
        return json.dumps({"error": "timeout"})
    except Exception as e:
        return json.dumps({"error": str(e)})
