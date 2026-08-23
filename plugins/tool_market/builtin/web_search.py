"""内置工具: web_search — 网络搜索 (DuckDuckGo / Google / Bing)"""

import json
import re
from urllib.parse import urljoin

import structlog

from plugins.security.network_policy import require_public_http_url, validate_http_url

logger = structlog.get_logger()


async def web_search(query: str, engine: str = "duckduckgo", limit: int = 5) -> str:
    """搜索网络"""
    if engine == "duckduckgo":
        return await _search_duckduckgo(query, limit)
    else:
        return json.dumps(
            {"error": f"Search engine '{engine}' requires API key"}, ensure_ascii=False
        )


async def _search_duckduckgo(query: str, limit: int = 5) -> str:
    """DuckDuckGo 搜索 (无 API Key 需要)"""
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
                results.append(
                    {
                        "title": data.get("AbstractSource", "DuckDuckGo"),
                        "snippet": data["AbstractText"],
                        "url": data.get("AbstractURL", ""),
                    }
                )

            # Related topics
            for topic in data.get("RelatedTopics", [])[:limit]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(
                        {
                            "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                            "snippet": topic["Text"],
                            "url": topic.get("FirstURL", ""),
                        }
                    )

            return json.dumps({"query": query, "results": results[:limit]}, ensure_ascii=False)

    except ImportError:
        # Fallback: 提示安装 httpx
        return json.dumps(
            {"error": "httpx not installed. Run: pip install httpx"}, ensure_ascii=False
        )
    except Exception as e:
        logger.warning("DuckDuckGo search failed", error=str(e))
        return json.dumps({"error": str(e), "query": query}, ensure_ascii=False)


_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json,text/plain;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
_JS_SHELL_MARKERS = (
    "enable javascript",
    "please enable javascript",
    "you need to enable javascript",
    "javascript is required",
)


def _validate_web_url(url: str) -> str:
    return validate_http_url(url)


def _normalize_text(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _extract_html(html: str, url: str, max_chars: int) -> dict:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else url

    ignored_tags = [
        "script",
        "style",
        "noscript",
        "template",
        "svg",
        "canvas",
        "nav",
        "footer",
        "header",
        "aside",
        "form",
    ]
    for tag in soup(ignored_tags):
        tag.decompose()

    candidates = [
        soup.find("article"),
        soup.find("main"),
        soup.find(attrs={"role": "main"}),
        soup.body,
    ]
    texts = [_normalize_text(node.get_text("\n", strip=True)) for node in candidates if node]
    text = max(texts, key=len, default="")
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars] + "..."
    return {
        "url": url,
        "title": title,
        "content": text,
        "content_length": len(text),
        "truncated": truncated,
        "extraction_method": "http",
    }


async def _fetch_static(url: str, max_chars: int) -> dict:
    import httpx

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        current_url = url
        for _ in range(6):
            await require_public_http_url(current_url)
            response = await client.get(current_url, headers=_REQUEST_HEADERS)
            if not response.is_redirect:
                break
            location = response.headers.get("location")
            if not location:
                raise ValueError("redirect response is missing a location")
            current_url = urljoin(str(response.url), location)
        else:
            raise ValueError("too many redirects")
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "html" in content_type or not content_type:
            result = _extract_html(response.text, str(response.url), max_chars)
        elif "text/" in content_type or "json" in content_type:
            text = _normalize_text(response.text)
            truncated = len(text) > max_chars
            result = {
                "url": str(response.url),
                "title": str(response.url),
                "content": text[:max_chars] + ("..." if truncated else ""),
                "content_length": min(len(text), max_chars),
                "truncated": truncated,
                "extraction_method": "http",
            }
        else:
            raise ValueError(f"unsupported content type: {content_type or 'unknown'}")
        result["status_code"] = response.status_code
        return result


def _needs_browser(result: dict) -> bool:
    content = result.get("content", "")
    lowered = content.lower()
    return len(content) < 200 or any(marker in lowered for marker in _JS_SHELL_MARKERS)


async def web_extract(url: str, render_js: bool = False, max_chars: int = 20000) -> str:
    """提取网页正文；静态内容不足时自动使用浏览器渲染。"""
    try:
        url = await require_public_http_url(url)
        max_chars = max(1000, min(int(max_chars), 50000))
    except (OSError, TypeError, ValueError) as error:
        return json.dumps({"error": str(error), "url": url}, ensure_ascii=False)

    static_result = None
    static_error = None
    try:
        static_result = await _fetch_static(url, max_chars)
    except ImportError as error:
        return json.dumps(
            {"error": f"Dependency missing: {error}", "url": url},
            ensure_ascii=False,
        )
    except Exception as error:
        static_error = str(error)

    if render_js or static_result is None or _needs_browser(static_result):
        try:
            from plugins.tool_market.builtin.browser import extract_rendered_page

            rendered = await extract_rendered_page(url, max_chars=max_chars)
            if rendered.get("content") or static_result is None:
                return json.dumps(rendered, ensure_ascii=False)
        except Exception as error:
            logger.info("Rendered web extraction unavailable", url=url, error=str(error))
            if static_result is None:
                return json.dumps(
                    {
                        "error": static_error or str(error),
                        "browser_error": str(error),
                        "hint": (
                            "Run 'playwright install chromium' to extract "
                            "JavaScript-rendered pages."
                        ),
                        "url": url,
                    },
                    ensure_ascii=False,
                )
            static_result["browser_fallback_error"] = str(error)

    return json.dumps(static_result, ensure_ascii=False)
