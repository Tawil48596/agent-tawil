"""GitLab MCP 适配器"""

import os

import httpx
import structlog

logger = structlog.get_logger()


class GitLabMCPAdapter:
    """将 GitLab REST API 映射为 MCP 工具"""

    BASE_URL = "https://gitlab.com/api/v4"

    def __init__(self, token: str = "", endpoint: str = ""):
        self._token = token or os.environ.get("GITLAB_TOKEN", "")
        self._endpoint = endpoint or os.environ.get("GITLAB_URL", self.BASE_URL)

    def list_tools(self) -> list[dict]:
        return [
            {
                "name": "gitlab_search_projects",
                "description": "搜索 GitLab 项目",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "gitlab_get_project",
                "description": "获取项目详情",
                "inputSchema": {
                    "type": "object",
                    "properties": {"project_id": {"type": "string"}},
                    "required": ["project_id"],
                },
            },
            {
                "name": "gitlab_list_files",
                "description": "列出项目文件",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "path": {"type": "string", "default": ""},
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "gitlab_read_file",
                "description": "读取文件内容",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "path": {"type": "string"},
                        "ref": {"type": "string", "default": "main"},
                    },
                    "required": ["project_id", "path"],
                },
            },
        ]

    async def call_tool(self, name: str, arguments: dict) -> dict:
        if not self._token:
            return {"error": "GitLab token not configured"}
        handler = getattr(self, f"_tool_{name}", None)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        try:
            return await handler(**arguments)
        except Exception as e:
            return {"error": str(e)}

    async def _tool_gitlab_search_projects(self, query: str, limit: int = 10) -> dict:
        async with httpx.AsyncClient(
            base_url=self._endpoint, headers={"PRIVATE-TOKEN": self._token}, timeout=15.0
        ) as c:
            r = await c.get("/projects", params={"search": query, "per_page": limit})
            return {
                "projects": [
                    {"name": p["name"], "path": p["path_with_namespace"], "url": p["web_url"]}
                    for p in r.json()[:limit]
                ]
            }

    async def _tool_gitlab_get_project(self, project_id: str) -> dict:
        pid = project_id.replace("/", "%2F")
        async with httpx.AsyncClient(
            base_url=self._endpoint, headers={"PRIVATE-TOKEN": self._token}, timeout=15.0
        ) as c:
            r = await c.get(f"/projects/{pid}")
            p = r.json()
            return {
                "name": p["name"],
                "description": p.get("description", ""),
                "url": p["web_url"],
                "default_branch": p.get("default_branch"),
            }

    async def _tool_gitlab_list_files(self, project_id: str, path: str = "") -> dict:
        pid = project_id.replace("/", "%2F")
        api_path = f"/projects/{pid}/repository/tree" + (f"?path={path}" if path else "")
        async with httpx.AsyncClient(
            base_url=self._endpoint, headers={"PRIVATE-TOKEN": self._token}, timeout=15.0
        ) as c:
            r = await c.get(api_path)
            return {
                "path": path or "/",
                "items": [
                    {"name": i["name"], "type": i["type"], "path": i["path"]} for i in r.json()
                ],
            }

    async def _tool_gitlab_read_file(self, project_id: str, path: str, ref: str = "main") -> dict:
        pid = project_id.replace("/", "%2F")
        from urllib.parse import quote

        encoded = quote(path, safe="")
        async with httpx.AsyncClient(
            base_url=self._endpoint, headers={"PRIVATE-TOKEN": self._token}, timeout=15.0
        ) as c:
            r = await c.get(f"/projects/{pid}/repository/files/{encoded}", params={"ref": ref})
            import base64

            data = r.json()
            content = base64.b64decode(data.get("content", "")).decode("utf-8")
            return {"path": path, "content": content, "size": data.get("size", 0)}
