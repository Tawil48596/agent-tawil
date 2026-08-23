"""会话分支 — 从任意对话点 fork"""

import json
import sqlite3
import uuid


class SessionBranch:
    """会话分支管理"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def fork(self, session_id: str, at_message_id: int, new_title: str = None) -> str | None:
        """从指定消息点创建分支"""
        parent = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not parent:
            return None

        branch_id = uuid.uuid4().hex[:12]
        title = new_title or f"{parent['title']} (分支)"

        self._conn.execute(
            """INSERT INTO sessions (id, title, source, parent_id, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (
                branch_id,
                title,
                parent["source"],
                session_id,
                json.dumps({"forked_at_msg": at_message_id}),
            ),
        )

        # 复制分叉点之前的消息
        messages = self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? AND id <= ? ORDER BY id",
            (session_id, at_message_id),
        ).fetchall()

        for msg in messages:
            self._conn.execute(
                "INSERT INTO messages "
                "(session_id, parent_msg_id, role, content, tool_calls, token_count) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    branch_id,
                    msg["parent_msg_id"],
                    msg["role"],
                    msg["content"],
                    msg["tool_calls"],
                    msg["token_count"],
                ),
            )

        self._conn.commit()
        return branch_id

    def get_branches(self, session_id: str) -> list[dict]:
        """获取某个会话的所有分支"""
        rows = self._conn.execute(
            "SELECT * FROM sessions WHERE parent_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
