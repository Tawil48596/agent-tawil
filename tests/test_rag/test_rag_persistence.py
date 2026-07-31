"""End-to-end persistence tests for the RAG subsystem."""

import pytest


def _rag_config(tmp_path):
    return {
        "vector_store": {
            "backend": "builtin",
            "builtin": {"path": str(tmp_path / "rag_vectors.json")},
        },
        "rag": {
            "metadata_path": str(tmp_path / "rag_metadata.json"),
            "retrieval_top_k": 10,
            "rerank_top_k": 5,
            "min_confidence": 0.0,
        },
    }


@pytest.mark.asyncio
async def test_rag_metadata_vectors_and_citations_survive_restart(tmp_path):
    from plugins.rag_engine.engine import RAGEngine

    config = _rag_config(tmp_path)
    first = RAGEngine(config)
    kb_id = await first.create_kb("Project docs", "Persistent test")
    document = await first.index_document_with_record(
        kb_id,
        "The deployment codename is aurora. Aurora uses SQLite locally.",
        {"source": "deployment.md", "filename": "deployment.md"},
        "fixed",
    )

    restarted = RAGEngine(config)
    knowledge_bases = await restarted.list_kbs()
    documents = await restarted.list_documents(kb_id)
    result = await restarted.query(
        "aurora", [kb_id], top_k=5, apply_guardrail=False
    )

    assert document["chunk_count"] == 1
    assert knowledge_bases[0]["document_count"] == 1
    assert documents[0]["id"] == document["id"]
    assert result["results"][0]["document_id"] == document["id"]
    assert result["results"][0]["citation"]["source"] == "deployment.md"


@pytest.mark.asyncio
async def test_deleting_document_removes_metadata_and_retrieval_chunks(tmp_path):
    from plugins.rag_engine.engine import RAGEngine

    config = _rag_config(tmp_path)
    engine = RAGEngine(config)
    kb_id = await engine.create_kb("Delete test")
    document = await engine.index_document_with_record(
        kb_id,
        "unique-removal-token belongs only to this document",
        {"source": "remove.txt"},
    )

    assert await engine.delete_document(kb_id, document["id"]) is True
    assert await engine.list_documents(kb_id) == []

    restarted = RAGEngine(config)
    result = await restarted.query(
        "unique-removal-token", [kb_id], top_k=5, apply_guardrail=False
    )
    assert result["results"] == []


@pytest.mark.asyncio
async def test_deleting_knowledge_base_removes_persistent_metadata(tmp_path):
    from plugins.rag_engine.engine import RAGEngine

    config = _rag_config(tmp_path)
    engine = RAGEngine(config)
    kb_id = await engine.create_kb("Temporary")
    await engine.index_document_with_record(kb_id, "temporary content")

    assert await engine.delete_kb(kb_id) is True
    assert await engine.delete_kb(kb_id) is False
    assert await RAGEngine(config).list_kbs() == []
