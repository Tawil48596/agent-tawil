"""Test RAG Chunkers"""

from plugins.rag_engine.chunker.code_aware import CodeAwareChunker
from plugins.rag_engine.chunker.fixed_size import FixedSizeChunker
from plugins.rag_engine.chunker.semantic import SemanticChunker


def test_fixed_chunker():
    fc = FixedSizeChunker(chunk_size=128)
    chunks = fc.chunk("Hello world. " * 50)
    assert len(chunks) >= 1


def test_semantic_chunker():
    sc = SemanticChunker()
    text = "# Title\n\nParagraph one.\n\n## Section\n\nParagraph two."
    result = sc.chunk_with_children(text)
    assert len(result) >= 1


def test_code_chunker_heuristic():
    cc = CodeAwareChunker()
    code = "import os\n\ndef func():\n    pass\n\nclass A:\n    def m(self):\n        return 1\n"
    chunks = cc.chunk(code)
    assert len(chunks) >= 1
