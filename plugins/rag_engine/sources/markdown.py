"""Markdown 文档源"""

from pathlib import Path


class MarkdownSource:
    """从 Markdown 文件索引文档"""

    async def fetch(self, file_path: str | Path) -> list[dict]:
        path = Path(file_path)
        if not path.exists():
            return []

        content = path.read_text(encoding="utf-8", errors="replace")
        return [
            {
                "content": content,
                "metadata": {
                    "source": str(path.absolute()),
                    "type": "markdown",
                    "filename": path.name,
                },
            }
        ]

    async def fetch_directory(self, dir_path: str, recursive: bool = True) -> list[dict]:
        path = Path(dir_path)
        if not path.exists():
            return []

        docs = []
        pattern = path.rglob("*.md") if recursive else path.glob("*.md")
        for f in pattern:
            docs.extend(await self.fetch(f))
        return docs
