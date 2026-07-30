"""Chat Service — 编排对话流程"""

from typing import AsyncIterator
from core.event_bus import Event, SESSION_UPDATED


class ChatService:
    def __init__(self, container):
        self._agent = container.resolve("AgentEngine")
        self._sessions = container.resolve("SessionStoreProtocol", "default")

    async def handle_message(self, session_id: str, content: str,
                              model: str = None) -> AsyncIterator[dict]:
        session = await self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        await self._sessions.add_message(session_id, role="user", content=content)

        async for event in self._agent.run_stream(
            user_message=content, session=session, override_model=model,
        ):
            yield event

        # 触发事件
        if hasattr(self, "_event_bus"):
            await self._event_bus.publish(Event(type=SESSION_UPDATED, source="chat_service",
                                                  data={"session_id": session_id}))
