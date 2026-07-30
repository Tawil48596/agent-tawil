"""Memory Service"""


class MemoryService:
    def __init__(self, long_term_memory, retrieval, consolidator, user_profile=None):
        self._ltm = long_term_memory
        self._retrieval = retrieval
        self._consolidator = consolidator
        self._profile = user_profile

    async def search(self, query: str, limit: int = 10) -> dict:
        return await self._retrieval.retrieve(query, limit)

    async def save(self, entry) -> str:
        return await self._ltm.save(entry)

    async def consolidate(self, messages: list[dict], session_id: str = "") -> list[str]:
        return await self._consolidator.consolidate(messages, session_id)

    def get_profile(self): return self._profile
