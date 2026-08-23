"""自定义命令 MCP 适配器 — 用户自定义命令注册"""

import asyncio


class CustomMCPAdapter:
    """用户自定义命令适配器"""

    def __init__(self):
        self._commands: dict[str, dict] = {}

    def register_command(
        self, name: str, command: str, description: str = "", workdir: str = "", timeout: int = 30
    ) -> None:
        self._commands[name] = {
            "command": command,
            "description": description,
            "workdir": workdir,
            "timeout": timeout,
        }

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": f"custom_{name}",
                "description": info["description"] or f"执行: {info['command']}",
                "inputSchema": {
                    "type": "object",
                    "properties": {"args": {"type": "string", "default": ""}},
                    "required": [],
                },
            }
            for name, info in self._commands.items()
        ]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        cmd_name = name.replace("custom_", "")
        cmd_info = self._commands.get(cmd_name)
        if not cmd_info:
            return {"error": f"Unknown custom command: {cmd_name}"}

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd_info["command"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cmd_info.get("workdir") or None,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=cmd_info.get("timeout", 30)
            )
            return {
                "stdout": stdout.decode("utf-8", errors="replace")[:5000],
                "stderr": stderr.decode("utf-8", errors="replace")[:1000],
                "exit_code": proc.returncode,
            }
        except TimeoutError:
            return {"error": "Command timed out"}
        except Exception as e:
            return {"error": str(e)}
