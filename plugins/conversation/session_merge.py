"""分支合并 — rebase/squash 策略 + 冲突处理"""

import sqlite3
from enum import StrEnum


class MergeStrategy(StrEnum):
    REBASE = "rebase"  # 追加到主会话末尾
    SQUASH = "squash"  # 压缩为一条摘要


class SessionMerge:
    """会话分支合并"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def merge(
        self,
        branch_id: str,
        strategy: MergeStrategy = MergeStrategy.REBASE,
        squash_summary: str = "",
    ) -> dict:
        """合并分支到主会话"""
        branch = self._conn.execute("SELECT * FROM sessions WHERE id = ?", (branch_id,)).fetchone()
        if not branch or not branch["parent_id"]:
            return {"error": "Not a branch session"}

        parent_id = branch["parent_id"]
        branch_msgs = self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id",
            (branch_id,),
        ).fetchall()

        if strategy == MergeStrategy.REBASE:
            for msg in branch_msgs:
                self._conn.execute(
                    """INSERT INTO messages (session_id, role, content, tool_calls, token_count)
                       VALUES (?, ?, ?, ?, ?)""",
                    (parent_id, msg["role"], msg["content"], msg["tool_calls"], msg["token_count"]),
                )

        elif strategy == MergeStrategy.SQUASH:
            summary = squash_summary or f"分支 {branch['title']} 的内容: " + "; ".join(
                m["content"][:50] for m in branch_msgs if m["content"]
            )
            self._conn.execute(
                """INSERT INTO messages (session_id, role, content)
                   VALUES (?, 'system', ?)""",
                (parent_id, f"[合并摘要] {summary}"),
            )

        # 更新主会话时间
        self._conn.execute(
            "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?",
            (parent_id,),
        )
        self._conn.commit()

        return {"ok": True, "strategy": strategy.value, "merged_messages": len(branch_msgs)}

    def resolve_conflict(self, session_id: str, msg_id: int, resolution: str) -> bool:
        """人工解决冲突"""
        # 标记冲突消息
        self._conn.execute(
            "UPDATE messages SET content = ? WHERE id = ?",
            (resolution, msg_id),
        )
        self._conn.commit()
        return True
