"""网页抓取文档源"""

import structlog

logger = structlog.get_logger()


class WebSource:
    """从网页索引文档"""

    async def fetch(self, url: str) -> list[dict]:
        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "ai-agent-platform/0.1"})
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
                return [{"content": text[:20000], "metadata": {"source": url, "type": "web"}}]
        except Exception as e:
            logger.warning("Web fetch failed", url=url, error=str(e))
            return []
