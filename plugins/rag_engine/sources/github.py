"""GitHub 仓库文档源"""

import os
from pathlib import Path
from typing import Optional


class GitHubSource:
    """从 GitHub 仓库索引文档"""

    def __init__(self, workspace: str = ""):
        self._workspace = Path(workspace or os.path.expanduser("~/agent_workspace"))

    async def fetch(self, owner: str, repo: str, branch: str = "main") -> list[dict]:
        """从已克隆的仓库读取文档"""
        repo_path = self._workspace / f"{owner}_{repo}"
        if not repo_path.exists():
            return []

        docs = []
        for ext in ["*.md", "*.rst", "*.txt"]:
            for f in repo_path.rglob(ext):
                if any(skip in str(f) for skip in [".git", "node_modules", "__pycache__"]):
                    continue
                content = f.read_text(encoding="utf-8", errors="replace")
                docs.append({
                    "content": content[:10000],
                    "metadata": {"source": f"github:{owner}/{repo}", "path": str(f.relative_to(repo_path)), "type": "markdown"},
                })
        return docs
