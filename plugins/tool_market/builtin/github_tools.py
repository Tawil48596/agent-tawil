"""内置工具: github_tools — GitHub 操作工具集"""
import json, os

async def github_search_repos(query: str, language: str = "", sort: str = "stars", limit: int = 10) -> str:
    try:
        import httpx
        token = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"} if token else {}
        async with httpx.AsyncClient(timeout=15) as c:
            q = f"{query} language:{language}" if language else query
            r = await c.get("https://api.github.com/search/repositories", params={"q": q, "sort": sort, "per_page": limit}, headers=headers)
            data = r.json()
            repos = [{"full_name": i["full_name"], "stars": i.get("stargazers_count",0), "url": i["html_url"]} for i in data.get("items",[])[:limit]]
            return json.dumps({"total": data.get("total_count",0), "repos": repos})
    except Exception as e: return json.dumps({"error": str(e)})
