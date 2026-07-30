"""RAG Service"""


class RAGService:
    def __init__(self, rag_engine):
        self._engine = rag_engine

    async def query(self, query: str, kb_ids: list[str] = None, top_k: int = 5) -> dict:
        return await self._engine.query(query, kb_ids, top_k)

    async def index(self, kb_id: str, content: str, metadata: dict = None, strategy: str = "fixed") -> int:
        return await self._engine.index_document(kb_id, content, metadata or {}, strategy)

    async def create_kb(self, name: str, description: str = "") -> str:
        return await self._engine.create_kb(name, description)
