"""内置工具: code_exec — 代码沙箱执行"""

import asyncio
import json
import os
import tempfile


async def code_exec(language: str, code: str, timeout: int = 30) -> str:
    try:
        if language == "python":
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                tmp = f.name
            try:
                proc = await asyncio.create_subprocess_exec(
                    "python", tmp, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                return json.dumps(
                    {
                        "stdout": stdout.decode(errors="replace")[:5000],
                        "stderr": stderr.decode(errors="replace")[:1000],
                        "exit_code": proc.returncode or 0,
                    }
                )
            finally:
                os.unlink(tmp)
        else:
            return json.dumps(
                {"error": f"Language '{language}' not supported for sandbox execution"}
            )
    except TimeoutError:
        return json.dumps({"error": "timeout"})
    except Exception as e:
        return json.dumps({"error": str(e)})
