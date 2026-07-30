"""固定大小分块 — 通用文本"""

import re


class FixedSizeChunker:
    """按固定 token 数分块 (估算: 1 token ≈ 4 字符)"""

    def __init__(self, chunk_size: int = 512, overlap: float = 0.1):
        self._chunk_size = chunk_size
        self._overlap = overlap
        self._char_size = chunk_size * 4  # 估算字符数

    def chunk(self, text: str) -> list[str]:
        if not text.strip():
            return []

        overlap_chars = int(self._char_size * self._overlap)
        chunks = []

        # 先按段落分割
        paragraphs = text.split("\n\n")
        current = ""

        for para in paragraphs:
            if len(current) + len(para) < self._char_size:
                current += para + "\n\n"
            else:
                if current.strip():
                    chunks.append(current.strip())
                current = para + "\n\n"

        if current.strip():
            chunks.append(current.strip())

        # 如果某个 chunk 仍然太大，强制按字符切分
        final = []
        for chunk in chunks:
            if len(chunk) <= self._char_size + overlap_chars:
                final.append(chunk)
            else:
                for i in range(0, len(chunk), self._char_size - overlap_chars):
                    sub = chunk[i:i + self._char_size]
                    if sub.strip():
                        final.append(sub.strip())

        return final
