"""导出 — JSONL / Markdown"""

import json
import sqlite3


class ConversationExporter:
    """会话导出"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def export_jsonl(self, session_id: str) -> str:
        """导出为 JSONL 格式"""
        messages = self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()

        lines = []
        for msg in messages:
            lines.append(
                json.dumps(
                    {
                        "id": msg["id"],
                        "role": msg["role"],
                        "content": msg["content"],
                        "tool_calls": json.loads(msg["tool_calls"] or "[]"),
                        "token_count": msg["token_count"],
                        "created_at": msg["created_at"],
                    },
                    ensure_ascii=False,
                )
            )

        return "\n".join(lines)

    def export_markdown(self, session_id: str) -> str:
        """导出为 Markdown 格式"""
        session = self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        messages = self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()

        title = session["title"] if session else "对话"
        lines = [
            f"# {title}",
            "",
            f"会话 ID: {session_id}",
            f"创建时间: {session['created_at']}",
            "",
            "---",
            "",
        ]

        for msg in messages:
            role_label = {
                "user": "👤 用户",
                "assistant": "🤖 Agent",
                "system": "📋 系统",
                "tool": "🔧 工具",
            }
            label = role_label.get(msg["role"], msg["role"])
            lines.append(f"### {label}")
            if msg["content"]:
                lines.append(msg["content"])
            tool_calls = json.loads(msg["tool_calls"] or "[]")
            if tool_calls:
                for tc in tool_calls:
                    lines.append(
                        f"- 🔧 `{tc.get('name', tc.get('function', {}).get('name', '?'))}`"
                    )
            lines.append("")

        return "\n".join(lines)
