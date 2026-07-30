"""会话持久化 — SQLite + FTS5 全文搜索"""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class SessionStore:
    """SQLite 会话存储 (含 FTS5 全文搜索)"""

    def __init__(self, db_path: str = "data/agent.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self):
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                title       TEXT DEFAULT '新对话',
                source      TEXT DEFAULT 'web',
                profile     TEXT,
                parent_id   TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                updated_at  TEXT DEFAULT (datetime('now')),
                metadata    TEXT DEFAULT '{}',
                FOREIGN KEY (parent_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT NOT NULL,
                parent_msg_id   INTEGER,
                role            TEXT NOT NULL,
                content         TEXT,
                tool_calls      TEXT DEFAULT '[]',
                token_count     INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                session_id, role, content
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
        """)
        self._conn.commit()

        # Rebuild FTS5 index from existing data
        self._conn.execute("INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')")
        self._conn.commit()

        # Initial FTS5 index population
        self._conn.execute("INSERT INTO messages_fts(messages_fts) VALUES ('rebuild')")
        self._conn.commit()

    # ── Session CRUD ──

    def create_session(self, title: str = "新对话", source: str = "web",
                        profile: str = None, metadata: dict = None) -> str:
        import uuid
        sid = uuid.uuid4().hex[:12]
        now = datetime.now().isoformat()
        self._conn.execute(
            """INSERT INTO sessions (id, title, source, profile, created_at, updated_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sid, title, source, profile, now, now, json.dumps(metadata or {}, ensure_ascii=False)),
        )
        self._conn.commit()
        return sid

    def get_session(self, session_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_sessions(self, limit: int = 50, offset: int = 0,
                       source: str = None) -> list[dict]:
        query = "SELECT * FROM sessions"
        params = []
        if source:
            query += " WHERE source = ?"
            params.append(source)
        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return [dict(r) for r in self._conn.execute(query, params).fetchall()]

    def update_session(self, session_id: str, title: str = None,
                        metadata: dict = None) -> bool:
        updates = []
        params = []
        if title:
            updates.append("title = ?")
            params.append(title)
        if metadata is not None:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata, ensure_ascii=False))
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(session_id)
            self._conn.execute(
                f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?", params
            )
            self._conn.commit()
            return True
        return False

    def delete_session(self, session_id: str) -> bool:
        # 先删消息 + FTS5
        self._conn.execute(
            "DELETE FROM messages_fts WHERE rowid IN (SELECT id FROM messages WHERE session_id = ?)",
            (session_id,),
        )
        self._conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cur = self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self._conn.commit()
        return cur.rowcount > 0

    # ── Message CRUD ──

    def add_message(self, session_id: str, role: str, content: str,
                     tool_calls: list = None, token_count: int = 0,
                     parent_msg_id: int = None) -> int:
        cur = self._conn.execute(
            """INSERT INTO messages (session_id, parent_msg_id, role, content, tool_calls, token_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, parent_msg_id, role, content,
             json.dumps(tool_calls or [], ensure_ascii=False), token_count),
        )
        msg_id = cur.lastrowid
        # Sync FTS5
        self._conn.execute(
            "INSERT INTO messages_fts(rowid, session_id, role, content) VALUES (?, ?, ?, ?)",
            (msg_id, session_id, role, content or ""),
        )
        # 更新 session 时间
        self._conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), session_id),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_messages(self, session_id: str, limit: int = 100, offset: int = 0) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC LIMIT ? OFFSET ?",
            (session_id, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Search ──

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """FTS5 全文搜索"""
        # 清理查询中的特殊字符
        clean_query = query.replace('"', '').replace("'", "")
        fts_query = " OR ".join(f'"{word}"' for word in clean_query.split() if word)

        rows = self._conn.execute(
            """SELECT m.* FROM messages m
               JOIN messages_fts fts ON m.id = fts.rowid
               WHERE messages_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (fts_query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_sessions(self, query: str, limit: int = 10) -> list[dict]:
        """搜索会话标题"""
        rows = self._conn.execute(
            "SELECT * FROM sessions WHERE title LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]
