"""语义分块 — 按段落/标题/Markdown 结构分块

Parent-Child Chunking: 小块用于检索，大块送入 LLM
- Child (256 tokens): 单个段落或语义单元，用于 Embedding 匹配
- Parent (1024 tokens): 包含周围上下文的更大块，送入 LLM
"""

import re


class SemanticChunker:
    """按语义边界分块 (Markdown 标题、段落)"""

    def __init__(self, child_size: int = 256, parent_size: int = 1024):
        self._child_char_size = child_size * 4
        self._parent_char_size = parent_size * 4

    def chunk(self, text: str) -> list[str]:
        """返回 parent-sized chunks (让 LLM 获得足够上下文)"""
        sections = self._split_by_sections(text)
        return self._merge_to_parent_size(sections)

    def chunk_with_children(self, text: str) -> list[dict]:
        """Parent-Child Chunking: 返回 {parent, children}"""
        sections = self._split_by_sections(text)
        parents = self._merge_to_parent_size(sections)

        # 简化版：每个 parent 包含的子 sections 作为 children
        result = []
        idx = 0
        for parent in parents:
            child_count = max(1, len(parent) // self._child_char_size)
            children = []
            for c in range(child_count):
                start = c * self._child_char_size
                end = start + self._child_char_size
                children.append(parent[start:end])
            result.append({"parent": parent, "children": children})

        return result

    def _split_by_sections(self, text: str) -> list[str]:
        """按标题和段落分块"""
        # 先按 ## 标题分割
        sections = re.split(r"\n(?=#{1,3}\s)", text)
        result = []
        for section in sections:
            # 再按双换行分段落
            paragraphs = section.split("\n\n")
            result.extend([p.strip() for p in paragraphs if p.strip()])
        return result

    def _merge_to_parent_size(self, sections: list[str]) -> list[str]:
        """将小 sections 合并到 parent 大小"""
        parents = []
        current = ""
        for section in sections:
            if len(current) + len(section) < self._parent_char_size:
                current += section + "\n\n"
            else:
                if current.strip():
                    parents.append(current.strip())
                current = section + "\n\n"
        if current.strip():
            parents.append(current.strip())
        return parents
