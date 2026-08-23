"""消息存储 — 按 session_id 分区"""

import json
import sqlite3
from datetime import datetime


class MessageStore:
    """消息持久化存储"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: list = None,
        token_count: int = 0,
        parent_msg_id: int = None,
    ) -> int:
        cur = self._conn.execute(
            "INSERT INTO messages "
            "(session_id, parent_msg_id, role, content, tool_calls, token_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_id,
                parent_msg_id,
                role,
                content,
                json.dumps(tool_calls or [], ensure_ascii=False),
                token_count,
            ),
        )
        self._conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), session_id),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_messages(
        self, session_id: str, limit: int = 100, offset: int = 0, before_id: int = None
    ) -> list[dict]:
        query = "SELECT * FROM messages WHERE session_id = ?"
        params = [session_id]
        if before_id:
            query += " AND id < ?"
            params.append(before_id)
        query += " ORDER BY id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return [dict(r) for r in self._conn.execute(query, params).fetchall()]

    def get_message(self, msg_id: int) -> dict | None:
        row = self._conn.execute("SELECT * FROM messages WHERE id = ?", (msg_id,)).fetchone()
        return dict(row) if row else None

    def delete_message(self, msg_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def count(self, session_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
        ).fetchone()
        return row[0] if row else 0
