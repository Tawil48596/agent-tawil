"""本地文件系统 MCP 适配器"""

import json
import os
from pathlib import Path


class FilesystemMCPAdapter:
    """本地文件系统 MCP 工具"""

    def __init__(self, workspace: str = ""):
        self._workspace = Path(workspace or os.path.expanduser("~/agent_workspace"))
        self._workspace.mkdir(parents=True, exist_ok=True)

    def list_tools(self) -> list[dict]:
        return [
            {"name": "fs_list", "description": "列出目录文件",
             "inputSchema": {"type": "object", "properties": {"path": {"type": "string", "default": "."}}, "required": []}},
            {"name": "fs_read", "description": "读取文件内容",
             "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
            {"name": "fs_write", "description": "写入文件",
             "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
            {"name": "fs_delete", "description": "删除文件",
             "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
        ]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        handler = getattr(self, f"_tool_{name}", None)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await handler(**arguments)
        except Exception as e:
            return {"error": str(e)}

    def _resolve(self, path: str) -> Path:
        p = self._workspace / path
        if not str(p.resolve()).startswith(str(self._workspace.resolve())):
            raise ValueError(f"Path outside workspace: {path}")
        return p

    async def _tool_fs_list(self, path: str = ".") -> dict:
        p = self._resolve(path)
        if not p.exists():
            return {"error": "Path not found"}
        items = []
        for f in p.iterdir():
            items.append({"name": f.name, "type": "dir" if f.is_dir() else "file", "size": f.stat().st_size if f.is_file() else 0})
        return {"path": str(p), "items": items[:100]}

    async def _tool_fs_read(self, path: str) -> dict:
        p = self._resolve(path)
        content = p.read_text(encoding="utf-8", errors="replace")
        return {"path": str(p), "content": content[:10000], "size": len(content)}

    async def _tool_fs_write(self, path: str, content: str) -> dict:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(p), "size": len(content)}

    async def _tool_fs_delete(self, path: str) -> dict:
        p = self._resolve(path)
        p.unlink()
        return {"ok": True, "path": str(p)}
