"""GitHub MCP 适配器 — 将 GitHub REST API 映射为 MCP 工具"""

import asyncio
import os
import time

import httpx
import structlog

from plugins.resilience.resilience_manager import CircuitBreaker

logger = structlog.get_logger()


class GitHubRateLimiter:
    """追踪 GitHub API 速率限制 (5000 req/h)"""

    def __init__(self):
        self._remaining = 5000
        self._reset_at: float = time.time() + 3600

    @property
    def remaining(self) -> int:
        if time.time() > self._reset_at:
            self._remaining = 5000
            self._reset_at = time.time() + 3600
        return self._remaining

    def update(self, remaining: int, reset_epoch: int):
        self._remaining = remaining
        self._reset_at = reset_epoch

    async def acquire(self) -> bool:
        if self.remaining <= 10:
            wait = self._reset_at - time.time()
            if wait > 0 and wait < 60:
                logger.info("Rate limit near, waiting", seconds=int(wait))
                await asyncio.sleep(wait + 1)
            elif wait > 0:
                return False
        self._remaining -= 1
        return True


class GitHubMCPAdapter:
    """将 GitHub REST API 映射为 MCP 工具集

    支持的 MCP 工具:
      - github_search_repos: 搜索仓库
      - github_get_repo: 获取仓库详情 + README
      - github_list_files: 列出文件结构
      - github_read_file: 读取文件内容
      - github_list_issues: 列出 Issues
      - github_search_code: 搜索代码
      - github_get_releases: 获取 Releases
      - github_clone_repo: 克隆仓库到工作区 (需 OAuth)
      - github_execute_action: 在克隆仓库中执行命令 (危险)
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str = "", config: dict = None):
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        cfg = config or {}
        self._rate_limiter = GitHubRateLimiter()
        self._circuit = CircuitBreaker(name="github_mcp", failure_threshold=5)
        self._client: httpx.AsyncClient | None = None
        self._workspace = os.path.expanduser(cfg.get("workspace", "~/agent_workspace"))
        os.makedirs(self._workspace, exist_ok=True)

    @property
    def is_configured(self) -> bool:
        return bool(self._token)

    # ── MCP 工具列表 ──

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": "github_search_repos",
                "description": "搜索 GitHub 仓库",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "language": {"type": "string", "description": "编程语言过滤"},
                        "sort": {"type": "string", "enum": ["stars", "forks", "updated"]},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "github_get_repo",
                "description": "获取仓库详情 + README",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "name": "github_list_files",
                "description": "列出仓库文件结构",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "path": {"type": "string", "default": ""},
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "name": "github_read_file",
                "description": "读取仓库中的文件内容",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "path": {"type": "string"},
                        "ref": {"type": "string", "description": "branch/tag/commit"},
                    },
                    "required": ["owner", "repo", "path"],
                },
            },
            {
                "name": "github_list_issues",
                "description": "列出仓库 Issues",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "state": {"type": "string", "enum": ["open", "closed", "all"]},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "name": "github_search_code",
                "description": "在 GitHub 上搜索代码",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "language": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "github_get_releases",
                "description": "获取仓库最新 Releases",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "limit": {"type": "integer", "default": 5},
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "name": "github_clone_repo",
                "description": "克隆仓库到本地工作区",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "branch": {"type": "string", "default": "main"},
                    },
                    "required": ["owner", "repo"],
                },
            },
            {
                "name": "github_create_branch",
                "description": "Create a GitHub branch from an existing ref",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "branch": {"type": "string"},
                        "from_ref": {"type": "string", "default": "main"},
                    },
                    "required": ["owner", "repo", "branch"],
                },
            },
            {
                "name": "github_update_file",
                "description": "Create or update a UTF-8 file and commit it",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "message": {"type": "string"},
                        "branch": {"type": "string"},
                        "sha": {"type": "string"},
                    },
                    "required": ["owner", "repo", "path", "content", "message", "branch"],
                },
            },
            {
                "name": "github_create_pull_request",
                "description": "Open a pull request for a prepared branch",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "title": {"type": "string"},
                        "head": {"type": "string"},
                        "base": {"type": "string", "default": "main"},
                        "body": {"type": "string"},
                        "draft": {"type": "boolean"},
                    },
                    "required": ["owner", "repo", "title", "head"],
                },
            },
        ]

    # ── 工具调用入口 ──

    async def call_tool(self, name: str, arguments: dict) -> dict:
        if not self.is_configured:
            return {"error": "GitHub token not configured. Set GITHUB_TOKEN env var."}

        if self._circuit.state.value == "open":
            return {"error": "GitHub API temporarily unavailable (circuit breaker open)"}

        handler = getattr(self, f"_tool_{name}", None)
        if not handler:
            return {"error": f"Unknown tool: {name}"}

        try:
            result = await handler(**arguments)
            self._circuit.success()
            return result
        except Exception as e:
            self._circuit.failure()
            logger.error("GitHub tool error", tool=name, error=str(e))
            return {"error": str(e)}

    # ── API 请求 ──

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "ai-agent-platform",
                },
                timeout=30.0,
            )
        return self._client

    async def _gh_get(self, path: str, params: dict = None) -> dict:
        if not await self._rate_limiter.acquire():
            return {"error": "GitHub API rate limit exceeded"}
        client = await self._get_client()
        resp = await client.get(path, params=params)
        self._rate_limiter.update(
            int(resp.headers.get("X-RateLimit-Remaining", 0)),
            int(resp.headers.get("X-RateLimit-Reset", time.time() + 3600)),
        )
        if resp.status_code == 403:
            return {"error": "Rate limit exceeded or access forbidden"}
        if resp.status_code == 404:
            return {"error": "Resource not found"}
        resp.raise_for_status()
        return resp.json()

    async def _gh_write(self, method: str, path: str, payload: dict) -> dict:
        if not await self._rate_limiter.acquire():
            return {"error": "GitHub API rate limit exceeded"}
        client = await self._get_client()
        response = await client.request(method, path, json=payload)
        if response.status_code == 404:
            return {"error": "Resource not found"}
        if response.status_code in (401, 403):
            return {"error": "GitHub write access denied"}
        if response.status_code == 422:
            detail = response.json().get("message", "GitHub rejected the operation")
            return {"error": detail}
        response.raise_for_status()
        return response.json()

    # ── 工具实现 ──

    async def _tool_github_search_repos(
        self, query: str, language: str = "", sort: str = "stars", limit: int = 10
    ) -> dict:
        q = query
        if language:
            q += f" language:{language}"
        data = await self._gh_get("/search/repositories", {"q": q, "sort": sort, "per_page": limit})
        if "error" in data:
            return data
        return {
            "total": data.get("total_count", 0),
            "repos": [
                {
                    "full_name": r["full_name"],
                    "description": r.get("description", ""),
                    "stars": r.get("stargazers_count", 0),
                    "forks": r.get("forks_count", 0),
                    "language": r.get("language"),
                    "url": r["html_url"],
                    "topics": r.get("topics", []),
                }
                for r in data.get("items", [])[:limit]
            ],
        }

    async def _tool_github_get_repo(self, owner: str, repo: str) -> dict:
        data = await self._gh_get(f"/repos/{owner}/{repo}")
        if "error" in data:
            return data
        return {
            "full_name": data["full_name"],
            "description": data.get("description", ""),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "language": data.get("language"),
            "topics": data.get("topics", []),
            "license": data.get("license", {}).get("spdx_id") if data.get("license") else None,
            "default_branch": data.get("default_branch"),
            "url": data["html_url"],
            "clone_url": data["clone_url"],
        }

    async def _tool_github_list_files(self, owner: str, repo: str, path: str = "") -> dict:
        api_path = (
            f"/repos/{owner}/{repo}/contents/{path}" if path else f"/repos/{owner}/{repo}/contents"
        )
        data = await self._gh_get(api_path)
        if "error" in data:
            return data
        if isinstance(data, list):
            return {
                "path": path or "/",
                "items": [
                    {
                        "name": d["name"],
                        "type": d["type"],
                        "path": d["path"],
                        "size": d.get("size", 0),
                    }
                    for d in data
                ],
            }
        return {"content": data}

    async def _tool_github_read_file(self, owner: str, repo: str, path: str, ref: str = "") -> dict:
        params = {"ref": ref} if ref else {}
        data = await self._gh_get(f"/repos/{owner}/{repo}/contents/{path}", params)
        if "error" in data:
            return data
        import base64

        content = data.get("content", "")
        if content:
            try:
                decoded = base64.b64decode(content).decode("utf-8")
                return {"path": path, "content": decoded, "size": data.get("size", 0)}
            except Exception:
                return {"path": path, "content": "[Binary file]", "size": data.get("size", 0)}
        return {"path": path, "content": ""}

    async def _tool_github_list_issues(
        self, owner: str, repo: str, state: str = "open", limit: int = 10
    ) -> dict:
        data = await self._gh_get(
            f"/repos/{owner}/{repo}/issues", {"state": state, "per_page": limit}
        )
        if "error" in data:
            return data
        return {
            "issues": [
                {
                    "number": i["number"],
                    "title": i["title"],
                    "state": i["state"],
                    "created_at": i["created_at"],
                    "url": i["html_url"],
                    "labels": [label["name"] for label in i.get("labels", [])],
                }
                for i in (data if isinstance(data, list) else [])[:limit]
            ],
        }

    async def _tool_github_search_code(
        self, query: str, language: str = "", limit: int = 10
    ) -> dict:
        q = query
        if language:
            q += f" language:{language}"
        data = await self._gh_get("/search/code", {"q": q, "per_page": limit})
        if "error" in data:
            return data
        return {
            "total": data.get("total_count", 0),
            "results": [
                {
                    "repo": r["repository"]["full_name"],
                    "path": r["path"],
                    "url": r["html_url"],
                }
                for r in data.get("items", [])[:limit]
            ],
        }

    async def _tool_github_get_releases(self, owner: str, repo: str, limit: int = 5) -> dict:
        data = await self._gh_get(f"/repos/{owner}/{repo}/releases", {"per_page": limit})
        if "error" in data:
            return data
        return {
            "releases": [
                {
                    "tag": r["tag_name"],
                    "name": r.get("name", ""),
                    "published_at": r.get("published_at"),
                    "url": r["html_url"],
                }
                for r in (data if isinstance(data, list) else [])[:limit]
            ],
        }

    async def _tool_github_clone_repo(self, owner: str, repo: str, branch: str = "main") -> dict:
        url = f"https://github.com/{owner}/{repo}.git"
        target = os.path.join(self._workspace, f"{owner}_{repo}")

        if os.path.exists(target):
            # 已存在 — 更新
            proc = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                target,
                "pull",
                "origin",
                branch,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        else:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                branch,
                url,
                target,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        return {
            "success": proc.returncode == 0,
            "path": target,
            "output": stdout.decode()[:500] if proc.returncode == 0 else stderr.decode()[:500],
        }

    async def _tool_github_create_branch(
        self, owner: str, repo: str, branch: str, from_ref: str = "main"
    ) -> dict:
        ref = await self._gh_get(f"/repos/{owner}/{repo}/git/ref/heads/{from_ref}")
        if "error" in ref:
            return ref
        result = await self._gh_write(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            {
                "ref": f"refs/heads/{branch}",
                "sha": ref["object"]["sha"],
            },
        )
        if "error" in result:
            return result
        return {
            "branch": branch,
            "sha": result.get("object", {}).get("sha"),
            "url": result.get("url"),
        }

    async def _tool_github_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str = "",
    ) -> dict:
        import base64

        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        result = await self._gh_write("PUT", f"/repos/{owner}/{repo}/contents/{path}", payload)
        if "error" in result:
            return result
        return {
            "path": path,
            "branch": branch,
            "commit_sha": result.get("commit", {}).get("sha"),
            "url": result.get("content", {}).get("html_url"),
        }

    async def _tool_github_create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
        draft: bool = False,
    ) -> dict:
        result = await self._gh_write(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            {
                "title": title,
                "head": head,
                "base": base,
                "body": body,
                "draft": draft,
            },
        )
        if "error" in result:
            return result
        return {
            "number": result.get("number"),
            "url": result.get("html_url"),
            "state": result.get("state"),
            "draft": result.get("draft", draft),
        }
