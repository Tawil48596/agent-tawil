"""内置工具: browser — Playwright 浏览器自动化"""

import json

import structlog

logger = structlog.get_logger()


async def _launch_browser(playwright):
    """Use bundled Chromium when present, otherwise reuse a system browser."""
    errors = []
    for options in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
        try:
            return await playwright.chromium.launch(headless=True, **options)
        except Exception as error:
            errors.append(str(error))
    raise RuntimeError(
        "No compatible Chromium browser is available. Run "
        "'playwright install chromium' or install Microsoft Edge/Google Chrome. "
        f"Last error: {errors[-1]}"
    )


async def extract_rendered_page(url: str, max_chars: int = 20000) -> dict:
    """Render a page with Chromium and return its visible body text."""
    from playwright.async_api import async_playwright

    from plugins.security.network_policy import require_public_http_url

    await require_public_http_url(url)
    async with async_playwright() as p:
        browser = await _launch_browser(p)
        try:
            page = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                )
            )

            approved_hosts = set()

            async def guard_request(route):
                from urllib.parse import urlparse

                hostname = urlparse(route.request.url).hostname
                try:
                    if hostname not in approved_hosts:
                        await require_public_http_url(route.request.url)
                        approved_hosts.add(hostname)
                    await route.continue_()
                except (OSError, ValueError):
                    await route.abort("blockedbyclient")

            await page.route("**/*", guard_request)
            response = await page.goto(url, wait_until="domcontentloaded", timeout=12000)
            await page.wait_for_timeout(500)
            title = await page.title()
            text = await page.locator("body").inner_text(timeout=3000)
            text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
            truncated = len(text) > max_chars
            if truncated:
                text = text[:max_chars] + "..."
            return {
                "url": page.url,
                "title": title or page.url,
                "content": text,
                "content_length": len(text),
                "truncated": truncated,
                "status_code": response.status if response else None,
                "extraction_method": "browser",
            }
        finally:
            await browser.close()


async def browser_navigate(url: str, max_chars: int = 20000) -> str:
    """浏览器导航到 URL 并返回页面内容"""
    try:
        result = await extract_rendered_page(url, max_chars=max_chars)
        return json.dumps(result, ensure_ascii=False)

    except ImportError:
        return json.dumps(
            {
                "error": (
                    "Playwright not installed. Run: pip install playwright "
                    "&& playwright install chromium"
                )
            }
        )
    except Exception as e:
        logger.warning("Browser navigate failed", url=url, error=str(e))
        return json.dumps({"error": str(e), "url": url})


async def browser_screenshot(url: str, selector: str = "body") -> str:
    """浏览器截图（返回 base64）"""
    try:
        import base64

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            element = await page.query_selector(selector) if selector else page
            if element:
                screenshot = await element.screenshot(type="png")
                b64 = base64.b64encode(screenshot).decode()
                await browser.close()
                return json.dumps(
                    {
                        "url": url,
                        "screenshot_base64": b64[:200] + "...",
                        "format": "png",
                        "note": "truncated for display",
                    }
                )
            await browser.close()
            return json.dumps({"error": f"Selector not found: {selector}"})

    except ImportError:
        return json.dumps({"error": "Playwright not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})
