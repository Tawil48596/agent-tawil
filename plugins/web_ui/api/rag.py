"""RAG API — 知识库 + 检索"""

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


class KBCreateRequest(BaseModel):
    name: str
    description: str = ""


class IndexRequest(BaseModel):
    content: str
    metadata: dict = {}
    chunk_strategy: str = "fixed"


class QueryRequest(BaseModel):
    query: str
    knowledge_bases: list[str] = []
    top_k: int = 5


@router.post("/knowledge-bases")
async def create_kb(body: KBCreateRequest, request: Request):
    kb_id = await request.app.state.rag_engine.create_kb(body.name, body.description)
    return {"id": kb_id, "name": body.name}


@router.get("/knowledge-bases")
async def list_kbs(request: Request):
    return {"knowledge_bases": await request.app.state.rag_engine.list_kbs()}


@router.delete("/knowledge-bases/{kb_id}")
async def delete_kb(kb_id: str, request: Request):
    await request.app.state.rag_engine.delete_kb(kb_id)
    return {"ok": True}


@router.post("/knowledge-bases/{kb_id}/documents")
async def index_document(kb_id: str, body: IndexRequest, request: Request):
    count = await request.app.state.rag_engine.index_document(
        kb_id, body.content, body.metadata, body.chunk_strategy,
    )
    return {"chunks_indexed": count}


@router.post("/query")
async def query(body: QueryRequest, request: Request):
    result = await request.app.state.rag_engine.query(
        body.query, body.knowledge_bases or None, body.top_k,
    )
    return result


@router.get("/chunkers")
async def list_chunkers():
    return {
        "chunkers": [
            {"id": "fixed", "name": "固定大小", "description": "通用文本, 512 tokens, 10% 重叠"},
            {"id": "semantic", "name": "语义分块", "description": "按标题/段落, Parent-Child Chunking"},
            {"id": "code", "name": "代码感知", "description": "Tree-sitter AST 分块, 保留函数签名和 import"},
        ]
    }
