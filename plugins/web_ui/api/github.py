"""GitHub Integration API"""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/v1/github", tags=["github"])


@router.get("/search/repos")
async def search_repos(
    q: str, language: str = "", sort: str = "stars", limit: int = 10, request: Request = None
):
    gw = request.app.state.mcp_gateway
    return await gw.call_tool(
        "github_search_repos", {"query": q, "language": language, "sort": sort, "limit": limit}
    )


@router.get("/repos/{owner}/{repo}")
async def get_repo(owner: str, repo: str, request: Request):
    gw = request.app.state.mcp_gateway
    return await gw.call_tool("github_get_repo", {"owner": owner, "repo": repo})


@router.get("/repos/{owner}/{repo}/tree")
async def repo_tree(owner: str, repo: str, path: str = "", request: Request = None):
    gw = request.app.state.mcp_gateway
    return await gw.call_tool("github_list_files", {"owner": owner, "repo": repo, "path": path})


@router.get("/repos/{owner}/{repo}/contents/{path:path}")
async def read_file(owner: str, repo: str, path: str, ref: str = "", request: Request = None):
    gw = request.app.state.mcp_gateway
    return await gw.call_tool(
        "github_read_file", {"owner": owner, "repo": repo, "path": path, "ref": ref}
    )


@router.post("/repos/{owner}/{repo}/clone")
async def clone_repo(owner: str, repo: str, branch: str = "main", request: Request = None):
    gw = request.app.state.mcp_gateway
    return await gw.call_tool("github_clone_repo", {"owner": owner, "repo": repo, "branch": branch})


@router.get("/workspaces")
async def list_workspaces(request: Request):
    import os

    workspace = os.path.expanduser("~/agent_workspace")
    import glob

    dirs = glob.glob(os.path.join(workspace, "*"))
    return {"workspaces": [{"path": d, "name": os.path.basename(d)} for d in dirs]}
