"""Session Service"""


class SessionService:
    def __init__(self, session_store, message_store):
        self._store = session_store
        self._messages = message_store

    def create_session(self, title: str = "新对话", source: str = "web") -> str:
        return self._store.create_session(title, source)

    def get_session(self, sid: str) -> dict:
        return self._store.get_session(sid)

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[dict]:
        return self._store.list_sessions(limit, offset)

    def delete_session(self, sid: str) -> bool:
        return self._store.delete_session(sid)

    def add_message(self, sid: str, role: str, content: str) -> int:
        return self._messages.add_message(sid, role, content)

    def get_messages(self, sid: str, limit: int = 100) -> list[dict]:
        return self._messages.get_messages(sid, limit)
