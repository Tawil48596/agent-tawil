"""代码仓库文档源"""

from pathlib import Path


class CodeSource:
    """从代码仓库索引文档"""

    CODE_EXTENSIONS = {".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c", ".h", ".rb", ".php"}

    async def fetch(self, repo_path: str, max_files: int = 100) -> list[dict]:
        path = Path(repo_path)
        if not path.exists():
            return []

        docs = []
        count = 0
        for f in path.rglob("*"):
            if count >= max_files:
                break
            if f.suffix in self.CODE_EXTENSIONS and ".git" not in str(f) and "node_modules" not in str(f):
                content = f.read_text(encoding="utf-8", errors="replace")
                docs.append({
                    "content": content[:5000],
                    "metadata": {"source": str(f.absolute()), "language": f.suffix[1:], "type": "code"},
                })
                count += 1
        return docs
