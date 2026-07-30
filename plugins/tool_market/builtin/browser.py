"""内置工具: browser — Playwright 浏览器自动化"""

import json

import structlog

logger = structlog.get_logger()


async def browser_navigate(url: str) -> str:
    """浏览器导航到 URL 并返回页面内容"""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            title = await page.title()
            text = await page.inner_text("body")
            await browser.close()

            if len(text) > 10000:
                text = text[:10000] + "..."

            return json.dumps({"url": url, "title": title, "content": text}, ensure_ascii=False)

    except ImportError:
        return json.dumps({"error": "Playwright not installed. Run: pip install playwright && playwright install chromium"})
    except Exception as e:
        logger.warning("Browser navigate failed", url=url, error=str(e))
        return json.dumps({"error": str(e), "url": url})


async def browser_screenshot(url: str, selector: str = "body") -> str:
    """浏览器截图（返回 base64）"""
    try:
        from playwright.async_api import async_playwright
        import base64

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            element = await page.query_selector(selector) if selector else page
            if element:
                screenshot = await element.screenshot(type="png")
                b64 = base64.b64encode(screenshot).decode()
                await browser.close()
                return json.dumps({"url": url, "screenshot_base64": b64[:200] + "...",
                                    "format": "png", "note": "truncated for display"})
            await browser.close()
            return json.dumps({"error": f"Selector not found: {selector}"})

    except ImportError:
        return json.dumps({"error": "Playwright not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})
