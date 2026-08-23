"""全文搜索历史会话"""

import sqlite3


class ConversationSearch:
    """全文搜索"""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def search_messages(self, query: str, limit: int = 20) -> list[dict]:
        """FTS5 全文搜索消息内容"""
        clean = query.replace('"', "").replace("'", "")
        fts_query = " OR ".join(f'"{w}"' for w in clean.split() if w)

        rows = self._conn.execute(
            """SELECT m.* FROM messages m
               JOIN messages_fts fts ON m.id = fts.rowid
               WHERE messages_fts MATCH ?
               ORDER BY rank LIMIT ?""",
            (fts_query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_sessions(self, title_query: str, limit: int = 10) -> list[dict]:
        """按标题搜索会话"""
        rows = self._conn.execute(
            "SELECT * FROM sessions WHERE title LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f"%{title_query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_all(self, query: str, limit: int = 20) -> dict:
        """综合搜索: 同时搜索消息和会话标题"""
        return {
            "messages": self.search_messages(query, limit),
            "sessions": self.search_sessions(query, limit),
        }
