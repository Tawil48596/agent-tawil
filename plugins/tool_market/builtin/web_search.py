"""内置工具: web_search — 网络搜索 (DuckDuckGo / Google / Bing)"""

import structlog

logger = structlog.get_logger()


async def web_search(query: str, engine: str = "duckduckgo", limit: int = 5) -> str:
    """搜索网络"""
    import json

    if engine == "duckduckgo":
        return await _search_duckduckgo(query, limit)
    else:
        return json.dumps({"error": f"Search engine '{engine}' requires API key"}, ensure_ascii=False)


async def _search_duckduckgo(query: str, limit: int = 5) -> str:
    """DuckDuckGo 搜索 (无 API Key 需要)"""
    import json

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            data = resp.json()

            results = []
            # Abstract
            if data.get("AbstractText"):
                results.append({
                    "title": data.get("AbstractSource", "DuckDuckGo"),
                    "snippet": data["AbstractText"],
                    "url": data.get("AbstractURL", ""),
                })

            # Related topics
            for topic in data.get("RelatedTopics", [])[:limit]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                        "snippet": topic["Text"],
                        "url": topic.get("FirstURL", ""),
                    })

            return json.dumps({"query": query, "results": results[:limit]}, ensure_ascii=False)

    except ImportError:
        # Fallback: 提示安装 httpx
        return json.dumps({"error": "httpx not installed. Run: pip install httpx"}, ensure_ascii=False)
    except Exception as e:
        logger.warning("DuckDuckGo search failed", error=str(e))
        return json.dumps({"error": str(e), "query": query}, ensure_ascii=False)


async def web_extract(url: str) -> str:
    """提取网页内容"""
    import json

    try:
        import httpx
        from bs4 import BeautifulSoup

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "ai-agent-platform/0.1"})
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # 提取主要文本
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            # 截断
            if len(text) > 5000:
                text = text[:5000] + "..."

            title = soup.title.string if soup.title else url

            return json.dumps({"url": url, "title": title, "content": text}, ensure_ascii=False)

    except ImportError as e:
        return json.dumps({"error": f"Dependency missing: {e}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e), "url": url}, ensure_ascii=False)
