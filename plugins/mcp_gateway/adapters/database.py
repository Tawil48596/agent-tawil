"""数据库 MCP 适配器"""

import json
import sqlite3
from pathlib import Path


class DatabaseMCPAdapter:
    """数据库查询 MCP 工具 (只读)"""

    def __init__(self, db_path: str = ""):
        self._db_path = db_path

    def list_tools(self) -> list[dict]:
        return [
            {"name": "db_query", "description": "执行只读 SQL 查询",
             "inputSchema": {"type": "object", "properties": {"sql": {"type": "string"}, "db_path": {"type": "string", "default": ""}}, "required": ["sql"]}},
            {"name": "db_list_tables", "description": "列出所有表",
             "inputSchema": {"type": "object", "properties": {"db_path": {"type": "string", "default": ""}}, "required": []}},
            {"name": "db_describe", "description": "查看表结构",
             "inputSchema": {"type": "object", "properties": {"table": {"type": "string"}, "db_path": {"type": "string", "default": ""}}, "required": ["table"]}},
        ]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        handler = getattr(self, f"_tool_{name}", None)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await handler(**arguments)
        except Exception as e:
            return {"error": str(e)}

    def _get_path(self, db_path: str) -> str:
        return db_path or self._db_path or "data/agent.db"

    async def _tool_db_query(self, sql: str, db_path: str = "") -> dict:
        path = self._get_path(db_path)
        if not Path(path).exists():
            return {"error": f"Database not found: {path}"}
        # 安全检查: 只允许 SELECT
        if not sql.strip().upper().startswith("SELECT"):
            return {"error": "Only SELECT queries are allowed"}
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql).fetchall()
        conn.close()
        return {"rows": [dict(r) for r in rows[:50]], "count": len(rows)}

    async def _tool_db_list_tables(self, db_path: str = "") -> dict:
        path = self._get_path(db_path)
        conn = sqlite3.connect(path)
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        return {"tables": tables}

    async def _tool_db_describe(self, table: str, db_path: str = "") -> dict:
        path = self._get_path(db_path)
        conn = sqlite3.connect(path)
        info = conn.execute(f"PRAGMA table_info({table})").fetchall()
        conn.close()
        return {"columns": [{"name": r[1], "type": r[2], "nullable": not r[3]} for r in info]}
