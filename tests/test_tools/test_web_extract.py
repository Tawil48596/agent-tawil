import json

import pytest

from plugins.tool_market.builtin import browser
from plugins.tool_market.builtin import web_search


def test_extract_html_prefers_visible_content_and_removes_navigation():
    result = web_search._extract_html(
        """
        <html><head><title>Example article</title><script>secret()</script></head>
        <body><header>Menu</header><main><h1>Heading</h1><p>Useful content.</p></main>
        <footer>Legal links</footer></body></html>
        """,
        "https://example.com/article",
        20000,
    )

    assert result["title"] == "Example article"
    assert result["content"] == "Heading\nUseful content."
    assert "Menu" not in result["content"]
    assert "secret" not in result["content"]


def test_extract_html_reports_truncation():
    result = web_search._extract_html(
        f"<html><body><main>{'x' * 1200}</main></body></html>",
        "https://example.com",
        1000,
    )

    assert result["truncated"] is True
    assert result["content"].endswith("...")


@pytest.mark.asyncio
async def test_web_extract_uses_browser_for_javascript_shell(monkeypatch):
    async def static_result(url, max_chars):
        return {
            "url": url,
            "title": "App",
            "content": "Please enable JavaScript to continue.",
            "content_length": 35,
            "truncated": False,
            "extraction_method": "http",
        }

    async def rendered_result(url, max_chars=20000):
        return {
            "url": url,
            "title": "Rendered app",
            "content": "The complete rendered article content.",
            "content_length": 38,
            "truncated": False,
            "extraction_method": "browser",
        }

    monkeypatch.setattr(web_search, "_fetch_static", static_result)
    monkeypatch.setattr(
        "plugins.tool_market.builtin.browser.extract_rendered_page",
        rendered_result,
    )

    result = json.loads(await web_search.web_extract("https://example.com/app"))

    assert result["extraction_method"] == "browser"
    assert result["content"] == "The complete rendered article content."


@pytest.mark.asyncio
async def test_web_extract_rejects_non_http_urls():
    result = json.loads(await web_search.web_extract("file:///etc/passwd"))

    assert "error" in result
    assert "HTTP(S)" in result["error"]


@pytest.mark.asyncio
async def test_browser_launch_falls_back_to_system_edge():
    class Chromium:
        def __init__(self):
            self.calls = []

        async def launch(self, **options):
            self.calls.append(options)
            if "channel" not in options:
                raise RuntimeError("bundled browser missing")
            return "browser"

    chromium = Chromium()
    result = await browser._launch_browser(type("Playwright", (), {"chromium": chromium})())

    assert result == "browser"
    assert chromium.calls == [{"headless": True}, {"headless": True, "channel": "msedge"}]
