"""MCP Gateway API — 管理 MCP Server 和工具"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


class ServerAddRequest(BaseModel):
    id: str
    name: str
    type: str = "custom"
    endpoint: str


@router.get("/servers")
async def list_servers(request: Request):
    """列出所有 MCP Server"""
    gw = request.app.state.mcp_gateway
    servers = gw.list_servers()
    return {
        "servers": [
            {"id": s.id, "name": s.name, "type": s.type,
             "status": s.status, "tools_count": s.tools_count}
            for s in servers
        ],
    }


@router.post("/servers")
async def add_server(body: ServerAddRequest, request: Request):
    """添加外部 MCP Server"""
    from plugins.mcp_gateway.gateway import MCPServerInfo
    gw = request.app.state.mcp_gateway
    info = MCPServerInfo(
        id=body.id, name=body.name, type=body.type, endpoint=body.endpoint,
    )
    await gw.register_server(info)
    return {"ok": True, "id": body.id}


@router.delete("/servers/{server_id}")
async def remove_server(server_id: str, request: Request):
    """移除 MCP Server"""
    gw = request.app.state.mcp_gateway
    await gw.unregister_server(server_id)
    return {"ok": True}


@router.get("/tools")
async def list_tools(request: Request):
    """列出所有 MCP 工具"""
    gw = request.app.state.mcp_gateway
    return {"tools": gw.list_all_tools()}


@router.post("/tools/{tool_name}/call")
async def call_tool(tool_name: str, body: dict, request: Request):
    """调用 MCP 工具"""
    gw = request.app.state.mcp_gateway
    result = await gw.call_tool(tool_name, body.get("arguments", {}))
    return result


@router.get("/github/search")
async def github_search(q: str, language: str = "", sort: str = "stars",
                         limit: int = 10, request: Request = None):
    """快捷 GitHub 搜索"""
    gw = request.app.state.mcp_gateway
    return await gw.call_tool("github_search_repos", {
        "query": q, "language": language, "sort": sort, "limit": limit,
    })
